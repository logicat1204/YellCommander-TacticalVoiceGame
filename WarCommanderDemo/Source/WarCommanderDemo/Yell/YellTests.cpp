#include "YellBattle.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "NavigationSystem.h"
#include "Serialization/JsonSerializer.h"
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
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->bMedic)
		{
			Test->TestTrue(TEXT("El médico selecciona al incapacitado indicado"), Battle->FindPatient(*Unit) == Patient);
		}
	}
	Patient->Treat(Now + 1);
	Test->TestTrue(TEXT("Reanimar recupera salud y capacidad de actuar"), Patient->CanAct() && Patient->Health > 0);
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
			FScreenshotRequest::RequestScreenshot(true);
		if (bUseService)
		{
			AYellPlayer* Player = Cast<AYellPlayer>(Battle->GetWorld()->GetFirstPlayerController());
			if (Player)
			{
				Player->bDetails = true;
				if (FParse::Param(FCommandLine::Get(), TEXT("YellTestModelB")))
				{
					Player->Model = TEXT("B");
				}
				if (FParse::Param(FCommandLine::Get(), TEXT("YellTestModelC")))
				{
					Player->Model = TEXT("C");
				}
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
