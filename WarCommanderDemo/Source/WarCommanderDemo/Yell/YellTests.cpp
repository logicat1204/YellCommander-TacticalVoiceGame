#include "YellBattle.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "HttpModule.h"
#include "InputCoreTypes.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "Layout/Children.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SWidget.h"
#include "YellPlayer.h"
#include "YellVoice.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellVoiceCaptureTest, "YellCommander.Voz.Captura",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FYellVoiceCaptureTest::RunTest(const FString& Parameters)
{
	constexpr int32 Rate = 48000, FrameCount = Rate / 2;
	TArray<float> Signal;
	Signal.Init(0.2f, FrameCount * 2);
	FYellVoiceBuffer InitialGap;
	InitialGap.Append(Signal.GetData(), FrameCount / 2, 2, Rate, true);
	InitialGap.Append(Signal.GetData(), FrameCount / 2, 2, Rate, false);
	const FYellVoiceTake Ready = InitialGap.Finish();
	TestTrue(TEXT("La discontinuidad del primer paquete se tolera"), Ready.Stats.Result() == EYellVoiceResult::Ready);
	TestTrue(TEXT("Registra la discontinuidad inicial"), Ready.Stats.bInitialGap && Ready.Stats.Gaps == 1);
	TestEqual(TEXT("WAV mono de 16 bits después de convertir estéreo"), Ready.Wave.Num(), 44 + FrameCount * 2);
	TestTrue(TEXT("La toma finalizada no se puede transmitir dos veces"), InitialGap.Finish().Wave.IsEmpty());

	FYellVoiceBuffer MidGap;
	MidGap.Append(Signal.GetData(), FrameCount / 2, 2, Rate, false);
	MidGap.Append(Signal.GetData(), FrameCount / 2, 2, Rate, true);
	const FYellVoiceTake Interrupted = MidGap.Finish();
	TestTrue(TEXT("Un corte después del inicio abstiene la transmisión"),
		Interrupted.Stats.Result() == EYellVoiceResult::Discontinuity && Interrupted.Wave.IsEmpty());

	FYellVoiceBuffer NoCallbacks;
	TestTrue(TEXT("Sin callbacks se distingue de una captura corta"), NoCallbacks.Snapshot().Result() == EYellVoiceResult::NoSamples);
	NoCallbacks.Append(Signal.GetData(), 256, 2, Rate, false);
	TestTrue(TEXT("Una pulsación menor de 250 ms es demasiado corta"), NoCallbacks.Snapshot().Result() == EYellVoiceResult::TooShort);
	NoCallbacks.Append(Signal.GetData(), 256, 2, 44100, false);
	TestTrue(TEXT("Rechaza un cambio de frecuencia durante la toma"), NoCallbacks.Snapshot().Result() == EYellVoiceResult::InvalidFormat);

	FYellVoiceBuffer Mute;
	Signal.Init(0.0f, FrameCount);
	Mute.Append(Signal.GetData(), FrameCount, 1, Rate, false);
	TestTrue(TEXT("Muestras sin señal se distinguen de falta de callbacks"), Mute.Snapshot().Result() == EYellVoiceResult::NoSignal);

	FYellVoiceBuffer Limited;
	Signal.Init(0.3f, Rate * FYellVoiceBuffer::MaxSeconds + 1);
	Limited.Append(Signal.GetData(), Signal.Num(), 1, Rate, false);
	const FYellVoiceTake Full = Limited.Finish();
	TestTrue(TEXT("No transmite un comando recortado por el límite"),
		Full.Stats.Result() == EYellVoiceResult::TimeLimit && Full.Wave.IsEmpty());
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_THREE_PARAMETER(FYellPhysicalCapture, FAutomationTestBase*, Test,
	TSharedPtr<FYellVoiceDevice>, Device, double, Started);

bool FYellPhysicalCapture::Update()
{
	if (FPlatformTime::Seconds() - Started < 1.15)
	{
		return false;
	}
	const FYellVoiceStats Stats = Device->Finish(false).Stats;
	Test->AddInfo(FString::Printf(TEXT("WASAPI: %s; %d Hz; %d canales; %d paquetes; %.0f ms; %d cortes; inicio=%d"),
		*Device->GetDeviceName(), Stats.Rate, Stats.Channels, Stats.Packets, Stats.AudioMs(), Stats.Gaps, Stats.bInitialGap));
	Test->TestTrue(TEXT("El dispositivo físico entregó más de 250 ms"), Stats.AudioMs() >= 250 && Stats.Packets > 1);
	Test->TestFalse(TEXT("El formato de los paquetes es compatible"), Stats.bInvalidFormat);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellVoiceDeviceTest, "YellCommander.Voz.Dispositivo",
	EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FYellVoiceDeviceTest::RunTest(const FString& Parameters)
{
	if (!FParse::Param(FCommandLine::Get(), TEXT("YellProbeMicrophone")))
	{
		AddInfo(TEXT("Activa -YellProbeMicrophone para abrir el dispositivo y contar muestras sin guardar audio."));
		return true;
	}
	TSharedPtr<FYellVoiceDevice> Device = MakeShared<FYellVoiceDevice>();
	const EYellVoiceResult Result = Device->Start();
	if (Result != EYellVoiceResult::Ready)
	{
		AddError(YellVoiceMessage(Result));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FYellPhysicalCapture(this, Device, FPlatformTime::Seconds()));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellContractTest, "YellCommander.Contrato",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FYellContractTest::RunTest(const FString& Parameters)
{
	const FString Document = TEXT(R"({"version":1,"intent":"orden","subject":{"type":"peloton","name":"Alfa"},"action":"avanzar","location":{"id":"centro"},"target":null,"model_confidence":null})");
	TSharedPtr<FJsonObject> Json;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Document), Json) || !Json)
	{
		AddError(TEXT("No se pudo cargar el ejemplo de contrato."));
		return false;
	}
	FYellOrder Order;
	FString Reason;
	TestTrue(TEXT("Acepta el esquema v1 con confianza nula"), YellOrder::Parse(*Json, Order, Reason));
	TestTrue(TEXT("Conserva acción y destinatario"), Order.Action == EYellAction::Advance && Order.Squad == TEXT("Alfa"));
	Json->SetStringField(TEXT("action"), TEXT("inventada"));
	TestFalse(TEXT("Rechaza una acción desconocida"), YellOrder::Parse(*Json, Order, Reason));
	Json->SetStringField(TEXT("action"), TEXT("avanzar"));
	Json->SetNumberField(TEXT("model_confidence"), 0.2);
	TestFalse(TEXT("Se abstiene con confianza baja"), YellOrder::Parse(*Json, Order, Reason));
	Json->SetNumberField(TEXT("model_confidence"), 0.97);
	Json->SetStringField(TEXT("extra"), TEXT("campo no autorizado"));
	TestFalse(TEXT("Rechaza campos adicionales"), YellOrder::Parse(*Json, Order, Reason));
	FYellReinforcements Queue;
	using EResult = FYellReinforcements::EResult;
	TestTrue(TEXT("No se permite un sexto pelotón"), Queue.Request(5, 120, 5, false, false) == EResult::Full);
	TestTrue(TEXT("No se permite un segundo médico"), Queue.Request(5, 120, 4, true, true) == EResult::MedicAlreadyActive);
	TestTrue(TEXT("Encola un único refuerzo"), Queue.Request(5, 120, 4, false, true) == EResult::Queued);
	bool bMedical = false;
	TestFalse(TEXT("El refuerzo requiere tiempo de llegada"), Queue.Collect(6, bMedical));
	TestTrue(TEXT("Entrega el refuerzo médico"), Queue.Collect(8, bMedical) && bMedical);
	TestFalse(TEXT("No entrega el mismo refuerzo dos veces"), Queue.Collect(9, bMedical));
	TestTrue(TEXT("Respeta el cooldown"), Queue.Request(30, 120, 4, false, false) == EResult::Busy);
	TestTrue(TEXT("Acepta después del cooldown"), Queue.Request(125, 120, 4, false, false) == EResult::Queued);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellDifficultyTest, "YellCommander.Dificultad",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FYellDifficultyTest::RunTest(const FString& Parameters)
{
	const auto Easy = FYellRivalPolicy::For(EYellDifficulty::Easy);
	const auto Normal = FYellRivalPolicy::For(EYellDifficulty::Normal);
	const auto Hard = FYellRivalPolicy::For(EYellDifficulty::Hard);
	TestTrue(TEXT("El intervalo se acorta con la dificultad"),
		Easy.IntelInterval > Normal.IntelInterval && Normal.IntelInterval > Hard.IntelInterval);
	TestTrue(TEXT("Fácil espera con una ventaja de 25 %"),
		Easy.Decide(false, false, false, true, true, false, 1.25f, true, false) == EYellRivalMove::Stage);
	TestTrue(TEXT("Difícil aprovecha una ventaja de 25 %"),
		Hard.Decide(false, false, false, true, true, false, 1.25f, true, false) == EYellRivalMove::Assault);
	TestTrue(TEXT("Difícil mantiene la reserva si no tiene cobertura"),
		Hard.Decide(false, false, false, true, false, false, 2.f, true, false) == EYellRivalMove::Stage);
	TestTrue(TEXT("Difícil también se repliega si queda superado"),
		Hard.Decide(false, false, true, true, true, false, .5f, false, false) == EYellRivalMove::Withdraw);
	TestTrue(TEXT("Se prioriza defender la base ante una emergencia"),
		Hard.Decide(true, true, false, true, true, false, 2.f, true, false) == EYellRivalMove::Guard);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellMedicalTest, "YellCommander.Medicos",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FYellMedicalTest::RunTest(const FString& Parameters)
{
	FYellMedicalSupplies Allied, Rival;
	TestEqual(TEXT("200 puntos disponibles al desplegar"), Allied.Status(0.).Healing, 200.f);
	TestEqual(TEXT("Se cura únicamente la cantidad solicitada"), Allied.SpendHealing(11., 18.f), 18.f);
	TestEqual(TEXT("Se descuenta la curación efectiva antes de alcanzar el tope"), Allied.SpendHealing(99., 177.f), 177.f);
	TestEqual(TEXT("La última curación se limita a la reserva"), Allied.SpendHealing(190., 18.f), 5.f);
	TestEqual(TEXT("Se agota la curación dentro del periodo"), Allied.SpendHealing(299., 18.f), 0.f);
	TestTrue(TEXT("Queda una reanimación aunque se haya agotado la curación"), Allied.SpendRevive(299.));
	TestFalse(TEXT("El mismo bando no puede reanimar una segunda vez"), Allied.SpendRevive(299.99));
	TestEqual(TEXT("El otro bando conserva su propia capacidad"), Rival.Status(299.).Healing, 200.f);
	TestTrue(TEXT("El rival tiene su propia reanimación"), Rival.SpendRevive(299.));
	TestEqual(TEXT("La curación se repone al minuto cinco exacto"), Allied.Status(300.).Healing, 200.f);
	TestTrue(TEXT("La reanimación también se repone"), Allied.SpendRevive(300.));
	TestEqual(TEXT("Las reservas no se acumulan entre periodos"), Allied.Status(900.).Healing, 200.f);
	return true;
}

class FYellMenuFlow final : public IAutomationLatentCommand
{
public:
	explicit FYellMenuFlow(FAutomationTestBase* InTest) : Test(InTest) {}
	bool Update() override;
private:
	FAutomationTestBase* Test;
	TWeakObjectPtr<AYellBattle> Match;
	TWeakObjectPtr<AYellSoldier> Patroller;
	FVector PatrolStart = FVector::ZeroVector;
	int32 Phase = 0;
	double PhaseStart = FPlatformTime::Seconds();
	const bool bCapture = FParse::Param(FCommandLine::Get(), TEXT("YellCapture"));
};

bool FYellMenuFlow::Update()
{
	AYellBattle* Battle = nullptr;
	for (const FWorldContext& Context : GEngine->GetWorldContexts())
	{
		if (Context.World() && (Battle = Context.World()->GetAuthGameMode<AYellBattle>())) break;
	}
	AYellPlayer* Player = Battle ? Cast<AYellPlayer>(Battle->GetWorld()->GetFirstPlayerController()) : nullptr;
	const double Now = FPlatformTime::Seconds();
	if (Now - PhaseStart > 40.)
	{
		Test->AddError(FString::Printf(TEXT("El flujo del menú no avanzó en la etapa %d."), Phase));
		return true;
	}
	if (!Player || !Battle->HasActorBegunPlay()) return false;
	using EPage = AYellPlayer::EMenuPage;
	const auto Capture = [&](const TCHAR* Name)
	{
		if (bCapture)
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("Screenshots") / Name, true, false);
	};
	switch (Phase)
	{
	case 0:
		if (!Battle->IsMenuScene() || !Player->HasMenu()) return false;
		Test->TestTrue(TEXT("El menú inicial usa la cámara del nivel"),
			Battle->GetMenuCamera() && Player->GetViewTarget() == Battle->GetMenuCamera());
		Test->TestEqual(TEXT("El menú muestra cinco actores"), Battle->Units().Num(), 5);
		for (const auto& Unit : Battle->Units())
		{
			if (!Unit.IsValid() || Unit->Squad != TEXT("Bravo")) continue;
			Patroller = Unit;
			PatrolStart = Unit->GetActorLocation();
			break;
		}
		break;
	case 1:
	{
		const bool bMoving = Patroller.IsValid() && FVector::Dist2D(PatrolStart, Patroller->GetActorLocation()) > 40.;
		if (Now - PhaseStart < (bMoving ? 1.5 : 7.)) return false;
		Test->TestTrue(TEXT("Un soldado se desplaza en la escena del menú"), bMoving);
		Capture(TEXT("YellMenuPrincipal.png"));
		break;
	}
	case 2:
		if (bCapture && FScreenshotRequest::IsScreenshotRequested()) return false;
		Player->ShowMenu(EPage::Settings);
		for (const auto Page : {EPage::Controls, EPage::Graphics, EPage::Audio})
		{
			Player->ShowMenu(Page);
			Test->TestTrue(TEXT("Existe una vista de configuración"), Player->HasMenu() && Player->MenuPage == Page);
			Player->BackFromMenu();
		}
		Player->ShowMenu(EPage::Difficulty);
		Test->TestTrue(TEXT("Se muestra el selector de dificultad"), Player->MenuPage == EPage::Difficulty);
		Capture(TEXT("YellMenuDificultad.png"));
		break;
	case 3:
		if (bCapture && FScreenshotRequest::IsScreenshotRequested()) return false;
		Player->StartMatch(EYellDifficulty::Hard);
		break;
	case 4:
		if (Battle->IsMenuScene() || !Player->GetPawn()) return false;
		Test->TestTrue(TEXT("La partida recibe la dificultad elegida"),
			!Player->HasMenu() && Battle->GetDifficulty() == EYellDifficulty::Hard);
		Player->EscapeMenu();
		Test->TestTrue(TEXT("Escape abre el menú y pausa la partida"),
			Player->HasMenu() && Player->MenuPage == EPage::Pause && Player->IsPaused());
		Match = Battle;
		break;
	case 5:
		if (Now - PhaseStart < .4) return false;
		Capture(TEXT("YellMenuPausa.png"));
		break;
	case 6:
	{
		if (bCapture && FScreenshotRequest::IsScreenshotRequested()) return false;
		if (!Player->HasMenu()) return true;
		const FYellRequestContext Context = Player->MakeContext();
		const FHttpRequestRef Pending = FHttpModule::Get().CreateRequest();
		Player->Requests.Add(Context.Id, Pending);
		Player->OnResponse(Pending, nullptr, false, Context, Now);
		Test->TestEqual(TEXT("La pausa conserva una respuesta recibida"), Player->PausedResponses.Num(), 1);
		const auto Root = Player->MenuView;
		const FKeyEvent Key(EKeys::Escape, FModifierKeysState(), 0, false, 0, 0);
		Root->OnKeyDown(FGeometry(), Key);
		Test->TestTrue(TEXT("Escape reanuda la partida y procesa la respuesta pendiente"),
			!Player->HasMenu() && !Player->IsPaused() && Player->PendingRequests() == 0);
		Player->EscapeMenu();
		Player->StartMatch(Battle->GetDifficulty());
		break;
	}
	case 7:
		if (Battle == Match.Get() || !Player->GetPawn()) return false;
		Test->TestTrue(TEXT("Reiniciar restaura una partida de la misma dificultad"),
			!Player->IsPaused() && Battle->GetDifficulty() == EYellDifficulty::Hard);
		Battle->DamageCore(1, 999.f);
		break;
	case 8:
		if (!Player->HasMenu() || Player->MenuPage != EPage::Result || Now - PhaseStart < .45) return false;
		Test->TestEqual(TEXT("La victoria abre la pantalla de resultado"), Battle->Winner(), 0);
		Capture(TEXT("YellResultado.png"));
		break;
	case 9:
	{
		if (bCapture && FScreenshotRequest::IsScreenshotRequested()) return false;
		TArray<TSharedRef<SWidget>> Pending = {Player->MenuView.ToSharedRef()};
		TSharedPtr<SButton> ReturnButton;
		while (!Pending.IsEmpty() && !ReturnButton)
		{
			const TSharedRef<SWidget> Widget = Pending.Pop();
			if (Widget->GetType() == TEXT("SYellMenuButton"))
			{
				ReturnButton = StaticCastSharedRef<SButton>(Widget);
			}
			else if (auto* Children = Widget->GetChildren())
			{
				for (int32 Index = 0; Index < Children->Num(); ++Index) Pending.Add(Children->GetChildAt(Index));
			}
		}
		if (!Test->TestTrue(TEXT("El resultado de victoria contiene un botón pulsable"), ReturnButton.IsValid())) return true;
		ReturnButton->SimulateClick();
		break;
	}
	case 10:
		if (!Battle->IsMenuScene() || !Player->HasMenu()) return false;
		Player->StartMatch(EYellDifficulty::Easy);
		break;
	case 11:
		if (Battle->IsMenuScene() || !Player->GetPawn()) return false;
		Battle->DamageCore(0, 999.f);
		break;
	case 12:
	{
		if (!Player->HasMenu() || Player->MenuPage != EPage::Result) return false;
		Test->TestEqual(TEXT("La derrota abre la pantalla de resultado"), Battle->Winner(), 1);
		const auto Root = Player->MenuView;
		const FKeyEvent Key(EKeys::Enter, FModifierKeysState(), 0, false, 0, 0);
		Test->TestTrue(TEXT("Confirmar en el resultado de derrota también vuelve al menú"), Root->OnKeyDown(FGeometry(), Key).IsEventHandled());
		break;
	}
	default:
		return Battle->IsMenuScene() && Player->HasMenu();
	}
	++Phase;
	PhaseStart = Now;
	return false;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellMenuTest, "YellCommander.Menu",
	EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FYellMenuTest::RunTest(const FString& Parameters)
{
	ADD_LATENT_AUTOMATION_COMMAND(FYellMenuFlow(this));
	return true;
}

class FYellEquipmentFlow final : public IAutomationLatentCommand
{
public:
	explicit FYellEquipmentFlow(FAutomationTestBase* InTest) : Test(InTest) {}
	bool Update() override;
private:
	FAutomationTestBase* Test;
	int32 Phase = 0;
	double PhaseStarted = FPlatformTime::Seconds();
	const bool bCapture = FParse::Param(FCommandLine::Get(), TEXT("YellEquipmentCapture"));
};

bool FYellEquipmentFlow::Update()
{
	UWorld* World = GEngine->GameViewport ? GEngine->GameViewport->GetWorld() : nullptr;
	auto* Player = World ? Cast<AYellPlayer>(World->GetFirstPlayerController()) : nullptr;
	auto* Commander = Player ? Player->GetPawn<AYellCommander>() : nullptr;
	const double Now = FPlatformTime::Seconds();
	if (Now - PhaseStarted > 15.)
	{
		Test->AddError(FString::Printf(TEXT("No avanzó la animación del equipo en la etapa %d."), Phase));
		if (Player)
		{
			Player->Requests.Reset();
			Player->ResetEquipmentInput();
		}
		return true;
	}
	if (!Commander || (bCapture && FScreenshotRequest::IsScreenshotRequested())) return false;
	auto Screenshot = [this](const TCHAR* Name)
	{
		if (bCapture)
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("Screenshots") / Name, true, false);
	};
	const bool bZoomed = Commander->OpticBlend() > .98f;
	const bool bNormal = !Commander->RadioModel->IsVisible() && !Commander->BinocularModel->IsVisible()
		&& Commander->OpticBlend() == 0.f && Commander->View->FieldOfView == AYellCommander::StandardFOV;
	switch (Phase)
	{
	case 0:
		Test->TestTrue(TEXT("El equipo está guardado al entrar"), bNormal);
		// Fill the request queue to exercise V without opening the physical microphone.
		for (int32 Index = 0; Index < AYellPlayer::MaxPending; ++Index)
			Player->Requests.Add(FGuid::NewGuid(), FHttpModule::Get().CreateRequest());
		Player->StartRecording();
		Test->TestTrue(TEXT("Pulsar V conserva la animación aunque el servicio está ocupado"),
			Player->bTalkHeld && !Player->bRecording);
		break;
	case 1:
		if (Commander->EquipmentLift < .99f) return false;
		if (bCapture && Now - PhaseStarted < .85) return false;
		Test->TestTrue(TEXT("Con radio activa se ve el walkie al hablar"),
			Commander->RadioModel->IsVisible() && !Commander->BinocularModel->IsVisible() && !bZoomed);
		Screenshot(TEXT("YellWalkieTalkie.png"));
		break;
	case 2:
		Player->StopRecording();
		break;
	case 3:
		if (!bNormal) return false;
		Player->bRadio = false;
		Player->StartRecording();
		break;
	case 4:
		if (Now - PhaseStarted < .25) return false;
		Test->TestTrue(TEXT("La voz de proximidad no levanta el walkie"), bNormal && Player->bTalkHeld);
		Player->StopRecording();
		Player->bRadio = true;
		Player->RaiseBinoculars();
		break;
	case 5:
		if (Commander->EquipmentLift < .65f) return false;
		Test->TestTrue(TEXT("Se ven las dos manos al levantar los binoculares"),
			Commander->BinocularModel->IsVisible() && !Commander->RadioModel->IsVisible());
		Screenshot(TEXT("YellLevantarBinoculares.png"));
		break;
	case 6:
		if (!bZoomed) return false;
		if (Now - PhaseStarted < .55) return false;
		Test->TestEqual(TEXT("El campo visual se estrecha en los binoculares"), Commander->View->FieldOfView, 30.f);
		Test->TestTrue(TEXT("Baja la sensibilidad del ratón con el aumento"), Player->LookScale() < Player->Sensitivity);
		Screenshot(TEXT("YellVistaBinocular.png"));
		break;
	case 7:
		Player->StartRecording();
		break;
	case 8:
		if (!Commander->RadioModel->IsVisible()) return false;
		Test->TestTrue(TEXT("V prioriza el walkie mientras el botón derecho sigue pulsado"),
			!Commander->BinocularModel->IsVisible() && Commander->OpticBlend() == 0.f && Player->bBinocularsHeld);
		Player->StopRecording();
		break;
	case 9:
		if (!bZoomed) return false;
		Player->LowerBinoculars();
		break;
	case 10:
		if (!bNormal) return false;
		Player->RaiseBinoculars();
		break;
	case 11:
		if (!bZoomed) return false;
		Player->EscapeMenu();
		Test->TestTrue(TEXT("Pausar guarda los binoculares y recupera la vista normal"), Player->IsPaused()
			&& Commander->OpticBlend() == 0.f && Commander->View->FieldOfView == AYellCommander::StandardFOV);
		Player->BackFromMenu();
		break;
	case 12:
		if (Now - PhaseStarted < .1) return false;
		Player->RaiseBinoculars();
		break;
	default:
		if (!bZoomed) return false;
		Player->FlushPressedKeys();
		Test->TestTrue(TEXT("Perder el foco restaura cámara y equipo"), Commander->OpticBlend() == 0.f
			&& !Commander->BinocularModel->IsVisible() && !Player->bBinocularsHeld);
		Player->Requests.Reset();
		return true;
	}
	++Phase;
	PhaseStarted = Now;
	return false;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellEquipmentTest, "YellCommander.Equipo",
	EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FYellEquipmentTest::RunTest(const FString& Parameters)
{
	ADD_LATENT_AUTOMATION_COMMAND(FYellEquipmentFlow(this));
	return true;
}

class FYellArenaCheck final : public IAutomationLatentCommand
{
public:
	explicit FYellArenaCheck(FAutomationTestBase* InTest) : Test(InTest) {}
	bool Update() override;
private:
	void CheckLayout(AYellBattle& Battle);
	FAutomationTestBase* Test;
	TWeakObjectPtr<ACameraActor> Camera;
	bool bShowHUD = true;
	int32 View = 0;
	double Started = FPlatformTime::Seconds();
	double ReadyAt = 0.;
	const bool bCapture = FParse::Param(FCommandLine::Get(), TEXT("YellArenaCapture"));
};

void FYellArenaCheck::CheckLayout(AYellBattle& Battle)
{
	UWorld* World = Battle.GetWorld();
	Test->TestEqual(TEXT("Campo de 308 por 156 metros"), Battle.ArenaExtent(), FVector2D(15400, 7800));
	Test->TestEqual(TEXT("Tres vías y cinco cruces laterales"), Battle.ArenaRoads().Num(), 13);
	FCollisionQueryParams Obstacles(SCENE_QUERY_STAT(YellRoadCheck), false, World->GetFirstPlayerController()->GetPawn());
	for (const auto& Unit : Battle.Units())
		if (Unit.IsValid()) Obstacles.AddIgnoredActor(Unit.Get());
	for (const FBox2D& Road : Battle.ArenaRoads())
	{
		const FVector2D Center = Road.GetCenter();
		const bool bAlongValley = Road.GetSize().X > Road.GetSize().Y;
		for (const double Offset : {-400., 0., 400.})
		{
			const FVector Start = bAlongValley ? FVector(Road.Min.X + 80., Center.Y + Offset, 85.)
				: FVector(Center.X + Offset, Road.Min.Y + 50., 85.);
			const FVector End = bAlongValley ? FVector(Road.Max.X - 80., Center.Y + Offset, 85.)
				: FVector(Center.X + Offset, Road.Max.Y - 50., 85.);
			Test->TestFalse(TEXT("La franja de circulación está libre de colisión"),
				World->LineTraceTestByChannel(Start, End, ECC_Pawn, Obstacles));
			if (Offset == 0.)
			{
				const auto* Path = UNavigationSystemV1::FindPathToLocationSynchronously(World, Start, End);
				Test->TestTrue(TEXT("La navegación cubre la vía completa"), Path && Path->IsValid() && !Path->IsPartial());
			}
		}
	}
	const TSet<FName> Expected = { TEXT("SM_Tienda_Militar"), TEXT("SM_Terminal_Refuerzos"), TEXT("SM_Mastil_Radio"),
		TEXT("SM_Cajas_Municion_Pila"), TEXT("SM_Barril_Combustible"), TEXT("SM_Alambrada_4m") };
	TSet<FName> Placed;
	int32 Terminals = 0;
	for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
	{
		for (const FName Tag : It->Tags)
		{
			if (!Expected.Contains(Tag) || (Placed.Contains(Tag) && Tag != TEXT("SM_Terminal_Refuerzos"))) continue;
			Placed.Add(Tag);
			auto* Mesh = It->GetStaticMeshComponent();
			const auto* Body = Mesh->GetBodySetup();
			Test->TestTrue(*FString::Printf(TEXT("%s tiene colisión y escala de escena"), *Tag.ToString()),
				Body && Body->AggGeom.GetElementCount() > 0 && Mesh->Bounds.BoxExtent.Z > 20. && Mesh->Bounds.BoxExtent.Z < 400.);
			if (Tag == TEXT("SM_Terminal_Refuerzos")) ++Terminals;
		}
	}
	Test->TestEqual(TEXT("Se colocaron los seis objetos del paquete"), Placed.Num(), Expected.Num());
	Test->TestEqual(TEXT("Cada base tiene una terminal"), Terminals, 2);
}

bool FYellArenaCheck::Update()
{
	UWorld* World = GEngine->GameViewport ? GEngine->GameViewport->GetWorld() : nullptr;
	AYellBattle* Battle = World ? World->GetAuthGameMode<AYellBattle>() : nullptr;
	APlayerController* Player = Battle ? World->GetFirstPlayerController() : nullptr;
	const double Now = FPlatformTime::Seconds();
	if (Now - Started > 35.)
	{
		Test->AddError(TEXT("El mapa ampliado no terminó de preparar la prueba."));
		return true;
	}
	if (!Player || !Player->GetPawn() || Battle->IsMenuScene() || Battle->WalkableTriangles().IsEmpty() ||
		UNavigationSystemV1::IsNavigationBeingBuilt(World)) return false;

	if (View == 0 && !Camera.IsValid())
	{
		CheckLayout(*Battle);
		if (!bCapture) return true;
		Camera = World->SpawnActor<ACameraActor>();
		Player->SetViewTarget(Camera.Get());
		bShowHUD = Player->GetHUD()->bShowHUD;
		Player->GetHUD()->bShowHUD = false;
	}
	if (FScreenshotRequest::IsScreenshotRequested()) return false;
	const TCHAR* Names[] = { TEXT("ValleAlfaCampamento.png"), TEXT("ValleAlfaCaminos.png"), TEXT("ValleAlfaTerminal.png") };
	if (View == UE_ARRAY_COUNT(Names))
	{
		Player->SetViewTarget(Player->GetPawn());
		Player->GetHUD()->bShowHUD = bShowHUD;
		Camera->Destroy();
		return true;
	}
	if (ReadyAt == 0.)
	{
		const FVector Core = Battle->CorePosition(0);
		const FVector Terminal = Battle->TerminalPosition(0);
		const FVector Positions[] = { Core + FVector(2430, -520, 950), FVector(-6500, -5800, 5500), Terminal + FVector(-123, 156, 155) };
		const FVector Targets[] = { Core + FVector(-120, 285, -50), FVector(1400, 750, 0), Terminal + FVector(0, 0, 105) };
		Camera->SetActorLocationAndRotation(Positions[View], (Targets[View] - Positions[View]).Rotation());
		ReadyAt = Now + 1.;
		return false;
	}
	if (Now < ReadyAt) return false;
	FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("Screenshots") / Names[View], true, false);
	++View;
	ReadyAt = 0.;
	return false;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellEnvironmentTest, "YellCommander.Ambiente",
	EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FYellEnvironmentTest::RunTest(const FString& Parameters)
{
	ADD_LATENT_AUTOMATION_COMMAND(FYellArenaCheck(this));
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_THREE_PARAMETER(FYellBattleScenario, FAutomationTestBase*, Test,
	TWeakObjectPtr<AYellBattle>, Game, double, Started);

bool FYellBattleScenario::Update()
{
	AYellBattle* Battle = Game.Get();
	if (!Battle)
	{
		Test->AddError(TEXT("El escenario terminó prematuramente."));
		return true;
	}
	UWorld* World = Battle->GetWorld();
	const double Now = World->GetTimeSeconds();
	const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
	FNavLocation Point;
	if (!Nav || !Nav->ProjectPointToNavigation(Battle->Position(EYellZone::Center, 0), Point))
	{
		if (FPlatformTime::Seconds() - Started < 20)
		{
			return false;
		}
		Test->AddError(TEXT("La malla de navegación no se generó."));
		return true;
	}
	for (const EYellZone Zone : {EYellZone::Left, EYellZone::Center, EYellZone::Right})
	{
		Test->TestTrue(TEXT("Cada carril tiene un destino navegable"),
			Nav->ProjectPointToNavigation(Battle->Position(Zone, 0), Point));
	}
	const AYellPlayer* Player = Cast<AYellPlayer>(World->GetFirstPlayerController());
	Test->TestTrue(TEXT("El nivel posee al comandante de primera persona"), Player && Player->GetPawn<AYellCommander>());
	FYellOrder Order;
	Order.Squad = TEXT("Alfa");
	Order.Action = EYellAction::Advance;
	Order.Zone = EYellZone::Center;
	bool bAccepted = false;
	FYellRequestContext Context{ FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now };
	Battle->Dispatch(Order, Context, bAccepted);
	Test->TestTrue(TEXT("Acepta una orden de radio válida"), bAccepted);
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Team == 0)
		{
			Test->TestEqual(TEXT("Solo Alfa recibió la orden"), Unit->CurrentOrder.Action == EYellAction::Advance, Unit->Squad == TEXT("Alfa"));
		}
	}
	Battle->Dispatch(Order, Context, bAccepted);
	Test->TestFalse(TEXT("Rechaza la misma identificación de solicitud"), bAccepted);
	FYellOrder Individual;
	Individual.Soldier = TEXT("Bravo-1");
	Individual.Action = EYellAction::Hold;
	Battle->Dispatch(Individual, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestTrue(TEXT("Un indicativo individual recibe la orden"), bAccepted);
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Squad == TEXT("Bravo"))
		{
			Test->TestEqual(TEXT("Solo Bravo-1 mantiene posición"), Unit->CurrentOrder.Action == EYellAction::Hold,
				Unit->CallSign == TEXT("Bravo-1"));
		}
	}
	Battle->Dispatch(Order, { FGuid::NewGuid(), EYellChannel::Nearby, FVector(4000, 2300, 100), Now }, bAccepted);
	Test->TestFalse(TEXT("Rechaza proximidad fuera del radio"), bAccepted);
	Order.Squad = TEXT("Inexistente");
	Battle->Dispatch(Order, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestFalse(TEXT("Rechaza pelotón inexistente"), bAccepted);
	Order.Squad = TEXT("Alfa");
	Order.Zone = EYellZone::None;
	Battle->Dispatch(Order, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestFalse(TEXT("Pide aclaración de destino"), bAccepted);
	FYellOrder Morale;
	Morale.Intent = EYellIntent::Morale;
	Battle->Dispatch(Morale, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestTrue(TEXT("Activa motivación de radio"), bAccepted && Battle->NextMorale() > 0);
	Battle->Dispatch(Morale, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestFalse(TEXT("Aplica cooldown de moral"), bAccepted);
	const FVector Terminal = Battle->TerminalPosition(0);
	Test->TestTrue(TEXT("Rechaza segundo médico"), Battle->TryReinforce(0, true, &Terminal).Contains(TEXT("médico activo")));
	Test->TestTrue(TEXT("Acepta refuerzos en terminal"), Battle->TryReinforce(0, false, &Terminal).Contains(TEXT("en camino")));
	Test->TestTrue(TEXT("Rechaza solicitudes de refuerzo simultáneas"), Battle->TryReinforce(0, false, &Terminal).Contains(TEXT("en curso")));

	AYellSoldier* Patient = nullptr;
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->Squad == TEXT("Bravo"))
		{
			Patient = Unit.Get();
			break;
		}
	}
	if (!Patient)
	{
		Test->AddError(TEXT("No se encontró un soldado para comprobar reanimación."));
		return true;
	}
	Patient->Hurt(500, Now);
	Test->TestTrue(TEXT("Incapacitar conserva al soldado en el pelotón"), Patient->IsAlive() && !Patient->CanAct());
	FYellOrder Heal;
	Heal.Action = EYellAction::Revive;
	Heal.Squad = TEXT("Médico");
	Heal.TargetSoldier = Patient->CallSign;
	Battle->Dispatch(Heal, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
	Test->TestTrue(TEXT("La orden médica individual se acepta"), bAccepted);
	AYellSoldier* Medic = nullptr;
	AYellSoldier* Partner = nullptr;
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->bMedic)
		{
			Test->TestTrue(TEXT("El médico selecciona al incapacitado indicado"), Battle->FindPatient(*Unit) == Patient);
			if (!Medic) Medic = Unit.Get();
			else Partner = Unit.Get();
		}
	}
	if (!Test->TestNotNull(TEXT("Primer médico"), Medic) || !Test->TestNotNull(TEXT("Segundo médico"), Partner)) return true;
	Battle->TreatPatient(*Medic, *Patient, Now + 1);
	Test->TestTrue(TEXT("Reanimar recupera salud y capacidad de actuar"), Patient->CanAct() && Patient->Health > 0);
	Test->TestEqual(TEXT("El uso de reanimación se refleja en el HUD"), Battle->MedicalStatus(0).Revives, 0);
	Test->TestEqual(TEXT("Reanimar usa su propia reserva"), Battle->MedicalStatus(0).Healing, 200.f);
	Patient->Hurt(500, Now + 1);
	Battle->TreatPatient(*Partner, *Patient, Now + 2);
	Test->TestFalse(TEXT("El segundo médico comparte el límite del primero"), Patient->CanAct());
	Test->TestNull(TEXT("El médico deja de seleccionar al caído si no dispone de reanimación"), Battle->FindPatient(*Partner));
	for (const auto& Unit : Battle->Units())
	{
		if (!Unit.IsValid() || Unit->Team != 0 || Unit->Squad != TEXT("Alfa") || !Unit->CanAct()) continue;
		Heal.Action = EYellAction::Heal;
		Heal.TargetSoldier = Unit->CallSign;
		Battle->Dispatch(Heal, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector, Now }, bAccepted);
		Unit->Hurt(4.f, Now);
		const float Missing = 100.f - Unit->Health;
		Battle->TreatPatient(*Partner, *Unit, Now + 2);
		Test->TestTrue(TEXT("Una cura pequeña descuenta únicamente los puntos recuperados"), Unit->Health == 100.f
			&& FMath::IsNearlyEqual(Battle->MedicalStatus(0).Healing, 200.f - Missing));
		break;
	}
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_FOUR_PARAMETER(FYellMotionScenario, FAutomationTestBase*, Test,
	TWeakObjectPtr<AYellBattle>, Game, double, Started, bool, bUseService);

bool FYellMotionScenario::Update()
{
	AYellBattle* Battle = Game.Get();
	if (!Battle)
	{
		Test->AddError(TEXT("El nivel finalizó antes de verificar el movimiento."));
		return true;
	}
	const AYellSoldier* Lead = nullptr;
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Squad == TEXT("Alfa") && Unit->CanAct())
		{
			Lead = Unit.Get();
			break;
		}
	}
	if (Lead && Lead->GetActorLocation().X > Battle->Position(EYellZone::Home, 0).X + 950.)
	{
		if (FParse::Param(FCommandLine::Get(), TEXT("YellCapture")))
			FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("Screenshots") / TEXT("YellHUDCombate.png"), true, false);
		if (bUseService)
		{
			AYellPlayer* Player = Cast<AYellPlayer>(Battle->GetWorld()->GetFirstPlayerController());
			if (Player)
			{
				Player->bDetails = true;
				if (FParse::Param(FCommandLine::Get(), TEXT("YellTestNearby")))
				{
					Player->bRadio = false;
					if (APawn* Commander = Player->GetPawn())
					{
						Commander->SetActorLocation(FVector(4000, 2300, 100));
					}
				}
				FString File;
				if (FParse::Value(FCommandLine::Get(), TEXT("YellTestWave="), File))
				{
					TArray<uint8> Wave;
					if (FFileHelper::LoadFileToArray(Wave, *File))
					{
						Player->SubmitTestWave(MoveTemp(Wave));
					}
					else
					{
						Test->AddError(TEXT("No se pudo leer la muestra WAV."));
					}
				}
				else
				{
					if (FParse::Param(FCommandLine::Get(), TEXT("YellTestConcurrent")))
					{
						Player->SubmitText(TEXT("Alex, ¿cómo estás?"));
						Player->SubmitText(TEXT("Juan, avancen al centro"));
						Player->SubmitText(TEXT("Bravo, defiendan nuestra base"));
						Player->SubmitText(TEXT("Diego, ¿cómo estás?"));
						Test->TestEqual(TEXT("Hay cuatro transmisiones activas"), Player->PendingRequests(), 4);
						Player->SubmitText(TEXT("Alfa, avancen por el centro"));
						Test->TestEqual(TEXT("La quinta transmisión no desplaza a las anteriores"), Player->PendingRequests(), 4);
					}
					else if (FParse::Param(FCommandLine::Get(),TEXT("YellTestChat")))
						Player->SubmitText(TEXT("Alex, ¿cómo estás?"));
					else if (FParse::Param(FCommandLine::Get(),TEXT("YellTestIndividual")))
						Player->SubmitText(TEXT("Juan, avancen al centro"));
					else
						Player->SubmitText(TEXT("Bravo, defiendan nuestra base"));
				}
			}
		}
		return true;
	}
	if (FPlatformTime::Seconds() - Started > 23)
	{
		Test->AddError(TEXT("Alfa no se desplazó hacia el centro mediante NavMesh."));
		return true;
	}
	return false;
}

DEFINE_LATENT_AUTOMATION_COMMAND_THREE_PARAMETER(FYellRivalDefenseScenario, FAutomationTestBase*, Test,
	TWeakObjectPtr<AYellBattle>, Game, double, HitTime);

DEFINE_LATENT_AUTOMATION_COMMAND_FOUR_PARAMETER(FYellFallScenario, FAutomationTestBase*, Test,
	TWeakObjectPtr<AYellBattle>, Game, TWeakObjectPtr<AYellSoldier>, Casualty, double, FellAt);

bool FYellFallScenario::Update()
{
	AYellBattle* Battle = Game.Get();
	if (!Battle) return true;
	const double Now = Battle->GetWorld()->GetTimeSeconds();
	if (FellAt == 0.)
	{
		const auto* Match = Battle->Units().FindByPredicate([](const auto& U)
		{
			return U.IsValid() && U->CallSign == TEXT("Bravo-4") && U->CanAct();
		});
		if (!Test->TestTrue(TEXT("Existe un soldado para comprobar la caída"), Match != nullptr))
			return true;
		Casualty = Match->Get();
		Casualty->SetActorLocation(Battle->SpawnPosition(0) + FVector(455, 30, 0));
		Casualty->Hurt(500.f, Now);
		FellAt = Now;
		return false;
	}
	if (Now < FellAt + 4.7) return false;
	if (auto* Unit = Casualty.Get())
	{
		Test->TestEqual(TEXT("El soldado queda incapacitado"), int32(Unit->State), int32(EYellSoldierState::Downed));
		TArray<FName> Bones;
		Unit->GetMesh()->GetBoneNames(Bones);
		const FName* Pelvis = Bones.FindByPredicate([](FName Bone)
		{
			return Bone.ToString().EndsWith(TEXT("Hips")) || Bone == TEXT("pelvis");
		});
		const bool bLow = Pelvis && Unit->GetMesh()->GetSocketLocation(*Pelvis).Z < Unit->GetActorLocation().Z - 26.;
		const bool bFallbackProne = FMath::Abs(Unit->GetMesh()->GetRelativeRotation().Roll) > 65.f;
		Test->TestTrue(TEXT("La baja queda tumbada sobre el suelo"), bLow || bFallbackProne);
	}
	else
		Test->AddError(TEXT("La baja desapareció antes de completar la caída."));
	if (FParse::Param(FCommandLine::Get(), TEXT("YellCapture")))
		FScreenshotRequest::RequestScreenshot(true);
	return true;
}

bool FYellRivalDefenseScenario::Update()
{
	AYellBattle* Battle = Game.Get();
	if (!Battle) return true;
	const double Now = FPlatformTime::Seconds();
	if (HitTime == 0.)
	{
		Battle->DamageCore(1, 14);
		HitTime = Now;
	}
	const bool bDefender = Battle->Units().ContainsByPredicate([](const auto& U)
	{
		return U.IsValid() && U->Team == 1 && !U->bMedic && U->CanAct() &&
			U->CurrentOrder.Zone == EYellZone::Home && U->CurrentOrder.Action == EYellAction::Defend;
	});
	if (!bDefender && Now - HitTime < 5.) return false;
	Test->TestTrue(TEXT("El primer daño al núcleo provoca una orden de defensa"), bDefender);
	Test->TestTrue(TEXT("El comandante rival solicita refuerzos cuando tiene espacio"), Battle->NextReinforcement(1) > 0.f);
	Test->TestTrue(TEXT("El minimapa tiene polígonos transitables reales"), Battle->WalkableTriangles().Num() > 3);
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_FOUR_PARAMETER(FYellVictoryScenario, FAutomationTestBase*, Test,
	TWeakObjectPtr<AYellBattle>, Game, double, Started, bool, bUseService);

bool FYellVictoryScenario::Update()
{
	AYellBattle* Battle = Game.Get();
	if (!Battle)
	{
		Test->AddError(TEXT("El nivel finalizó antes de verificar la victoria."));
		return true;
	}
	if (bUseService)
	{
		const AYellPlayer* Player = Cast<AYellPlayer>(Battle->GetWorld()->GetFirstPlayerController());
		FString File;
		const bool bWave = FParse::Value(FCommandLine::Get(), TEXT("YellTestWave="), File);
		const bool bNearby = FParse::Param(FCommandLine::Get(), TEXT("YellTestNearby"));
		const TCHAR* Expected = FParse::Param(FCommandLine::Get(),TEXT("YellTestChat")) ? TEXT("Alex: ")
			: FParse::Param(FCommandLine::Get(),TEXT("YellTestIndividual")) ? TEXT("Copiado, Juan")
			: bNearby ? TEXT("Ningún soldado disponible recibió la transmisión")
			: bWave ? TEXT("Copiado, Alfa") : TEXT("Copiado, Bravo");
		const bool bConcurrent = FParse::Param(FCommandLine::Get(), TEXT("YellTestConcurrent"));
		const bool bWaiting = Player && (bConcurrent
			? Player->PendingRequests() > 0 || Player->PendingAudio() > 0 : !Player->Status.Contains(Expected));
		if (bWaiting)
		{
			if (FPlatformTime::Seconds() - Started < 35)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("La orden HTTP no llegó al pelotón previsto. Estado: %s"), *Player->Status));
		}
		else if (!Player)
		{
			Test->AddError(TEXT("No existe el controlador de la orden textual."));
		}
		else if (bConcurrent)
		{
			for (const TCHAR* Entry : {TEXT("Alex: "), TEXT("Diego: "), TEXT("Copiado, Bravo"), TEXT("Copiado, Juan")})
			{
				Test->TestTrue(Entry, Player->Recent.ContainsByPredicate(
					[Entry](const FString& Reply) { return Reply.Contains(Entry); }));
			}
		}
	}
	FYellOrder Assault;
	Assault.Squad = TEXT("Alfa");
	Assault.Action = EYellAction::Attack;
	Assault.Zone = EYellZone::Rival;
	bool bAccepted = false;
	Battle->Dispatch(Assault, { FGuid::NewGuid(), EYellChannel::Radio, FVector::ZeroVector,
		Battle->GetWorld()->GetTimeSeconds() }, bAccepted);
	Test->TestTrue(TEXT("Alfa acepta atacar el núcleo rival"), bAccepted);
	AYellSoldier* Attacker = nullptr;
	AYellSoldier* Defender = nullptr;
	for (const auto& Unit : Battle->Units())
	{
		if (!Unit.IsValid() || !Unit->CanAct()) continue;
		if (Unit->Team == 0 && Unit->Squad == TEXT("Alfa")) Attacker = Unit.Get();
		if (Unit->Team == 1) Defender = Unit.Get();
	}
	if (Test->TestNotNull(TEXT("Hay atacante"), Attacker) && Test->TestNotNull(TEXT("Hay defensor"), Defender))
	{
		Attacker->SetActorLocation(Battle->CorePosition(1) - FVector(490, 0, 0));
		const float PreviousHealth = Battle->CoreHealth(1);
		Battle->SimulatePulse(*Attacker, Defender, Defender->Eye());
		Test->TestTrue(TEXT("La orden prioriza el núcleo visible aunque haya un defensor"),
			Battle->CoreHealth(1) < PreviousHealth);
	}
	Battle->DamageCore(1, 999);
	Test->TestEqual(TEXT("La destrucción de la base rival otorga victoria"), Battle->Winner(), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FYellLiveTest, "YellCommander.Partida",
	EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FYellLiveTest::RunTest(const FString& Parameters)
{
	AYellBattle* Battle = nullptr;
	for (const FWorldContext& Context : GEngine->GetWorldContexts())
	{
		if (Context.World() && (Battle = Context.World()->GetAuthGameMode<AYellBattle>()))
		{
			break;
		}
	}
	if (!Battle)
	{
		AddError(TEXT("Ejecute la prueba desde ValleAlfa en modo -game."));
		return false;
	}
	const double Now = FPlatformTime::Seconds();
	const bool bService = FParse::Param(FCommandLine::Get(), TEXT("YellTestService"));
	ADD_LATENT_AUTOMATION_COMMAND(FYellBattleScenario(this, Battle, Now));
	ADD_LATENT_AUTOMATION_COMMAND(FYellMotionScenario(this, Battle, Now, bService));
	ADD_LATENT_AUTOMATION_COMMAND(FYellFallScenario(this, Battle, nullptr, 0.));
	ADD_LATENT_AUTOMATION_COMMAND(FYellRivalDefenseScenario(this, Battle, 0.));
	ADD_LATENT_AUTOMATION_COMMAND(FYellVictoryScenario(this, Battle, Now, bService));
	return true;
}
#endif
