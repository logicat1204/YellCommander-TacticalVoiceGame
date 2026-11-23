#include "YellPlayer.h"

#include "Audio.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HttpModule.h"
#include "InputCoreTypes.h"
#include "Interfaces/IHttpResponse.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Base64.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundWaveProcedural.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"
#include "UnrealClient.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "YellBattle.h"

DEFINE_LOG_CATEGORY_STATIC(LogYellVoice, Log, All);

AYellCommander::AYellCommander()
{
	GetCapsuleComponent()->InitCapsuleSize(34.0f, 88.0f);
	View = CreateDefaultSubobject<UCameraComponent>(TEXT("CommanderView"));
	View->SetupAttachment(GetCapsuleComponent());
	View->SetRelativeLocation(FVector(0, 0, 68));
	View->bUsePawnControlRotation = true;
	View->SetFieldOfView(94);
	GetCharacterMovement()->MaxWalkSpeed = 640;
	GetCharacterMovement()->JumpZVelocity = 440;
}

void AYellCommander::Hurt(const float Damage)
{
	if (HitPoints <= 0)
	{
		return;
	}
	HitPoints = FMath::Max(0.0f, HitPoints - Damage);
	if (HitPoints <= 0)
	{
		GetCharacterMovement()->DisableMovement();
		GetWorldTimerManager().SetTimer(RespawnTimer, this, &AYellCommander::Recover, 4.0f);
	}
}

void AYellCommander::Recover()
{
	const AYellBattle* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	if (!Battle || Battle->Winner() != INDEX_NONE)
	{
		return;
	}
	TeleportTo(Battle->SpawnPosition(0), FRotator::ZeroRotator);
	if (AController* OwnerController = GetController())
	{
		OwnerController->SetControlRotation(FRotator::ZeroRotator);
	}
	HitPoints = 100.0f;
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
}

AYellPlayer::AYellPlayer()
{
	static ConstructorHelpers::FObjectFinderOptional<USoundBase> Acknowledge(
		TEXT("/Game/Yell/Audio/RadioCopiado.RadioCopiado"));
	static ConstructorHelpers::FObjectFinderOptional<USoundBase> Clarify(
		TEXT("/Game/Yell/Audio/RadioAclarar.RadioAclarar"));
	static ConstructorHelpers::FObjectFinderOptional<USoundBase> Morale(
		TEXT("/Game/Yell/Audio/RadioMoral.RadioMoral"));
	AcknowledgeCue = Acknowledge.Get();
	ClarifyCue = Clarify.Get();
	MoraleCue = Morale.Get();
}

void AYellPlayer::BeginPlay()
{
	Super::BeginPlay();
	if (IsLocalController())
	{
		SetInputMode(FInputModeGameOnly());
		FString Configured;
		if (FParse::Value(FCommandLine::Get(), TEXT("YellModels="), Configured))
		{
			TArray<FString> Names;
			Configured.ParseIntoArray(Names, TEXT(","));
			AvailableModels.Reset();
			for (const FString& Name : Names)
			{
				if (Name == TEXT("A") || Name == TEXT("B") || Name == TEXT("C") || Name == TEXT("D"))
				{
					AvailableModels.AddUnique(Name);
				}
			}
			if (AvailableModels.IsEmpty())
			{
				AvailableModels.Add(TEXT("A"));
			}
			AvailableModels.Sort();
			Model = AvailableModels.Contains(TEXT("A")) ? TEXT("A") : AvailableModels[0];
		}
	}
}

void AYellPlayer::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (!InputComponent)
	{
		return;
	}
	InputComponent->BindAxisKey(EKeys::MouseX, this, &AYellPlayer::LookX);
	InputComponent->BindAxisKey(EKeys::MouseY, this, &AYellPlayer::LookY);
	InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AYellPlayer::Jump);
	InputComponent->BindKey(EKeys::V, IE_Pressed, this, &AYellPlayer::StartRecording);
	InputComponent->BindKey(EKeys::V, IE_Released, this, &AYellPlayer::StopRecording);
	InputComponent->BindKey(EKeys::T, IE_Pressed, this, &AYellPlayer::OpenConsole);
	InputComponent->BindKey(EKeys::R, IE_Pressed, this, &AYellPlayer::ToggleRadio);
	InputComponent->BindKey(EKeys::F2, IE_Pressed, this, &AYellPlayer::ToggleModel);
	InputComponent->BindKey(EKeys::F3, IE_Pressed, this, &AYellPlayer::ToggleDetails);
	InputComponent->BindKey(EKeys::F4, IE_Pressed, this, &AYellPlayer::ToggleSpeech);
	InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AYellPlayer::Reinforce);
	InputComponent->BindKey(EKeys::F, IE_Pressed, this, &AYellPlayer::ReinforceMedic);
	InputComponent->BindKey(EKeys::F5, IE_Pressed, this, &AYellPlayer::RestartBattle);
}

void AYellPlayer::PlayerTick(const float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	UpdateAudio();
	if (bRecording)
	{
		const double Now = FPlatformTime::Seconds();
		if (!HasVoiceFocus())
		{
			FinishRecording(EYellVoiceResult::FocusLost);
		}
		else if (!CanTransmit())
		{
			FinishRecording(EYellVoiceResult::Interrupted);
		}
		else if (Now - CaptureStarted >= FYellVoiceBuffer::MaxSeconds)
		{
			FinishRecording(EYellVoiceResult::TimeLimit);
		}
		else if (Now >= NextMicUpdate)
		{
			const FYellVoiceStats Stats = Capture->Snapshot();
			if (!bMicReady && Stats.Frames > 0)
			{
				bMicReady = true;
				Status = TEXT("Habla ahora. Suelta V al terminar.");
			}
			const float Signal = FMath::Clamp((Stats.PeakDbfs() + 60.0) / 60.0, 0.0, 1.0);
			MicLevel = Signal;
			VoiceDiagnostics = FString::Printf(TEXT("Mic %.2f s · %d Hz · %d paquetes · %d cortes · pico %.0f dBFS"),
				Stats.AudioMs() / 1000.0, Stats.Rate, Stats.Packets, Stats.Gaps, Stats.PeakDbfs());
			NextMicUpdate = Now + 0.10;
		}
	}
	if (!Console && CanTransmit())
	{
		const FRotationMatrix Axes(FRotator(0, GetControlRotation().Yaw, 0));
		const float Forward = static_cast<float>(IsInputKeyDown(EKeys::W)) - static_cast<float>(IsInputKeyDown(EKeys::S));
		const float Right = static_cast<float>(IsInputKeyDown(EKeys::D)) - static_cast<float>(IsInputKeyDown(EKeys::A));
		GetPawn()->AddMovementInput(Axes.GetScaledAxis(EAxis::X), Forward);
		GetPawn()->AddMovementInput(Axes.GetScaledAxis(EAxis::Y), Right);
	}
}

void AYellPlayer::FlushPressedKeys()
{
	if (bRecording)
	{
		FinishRecording(EYellVoiceResult::FocusLost);
	}
	Super::FlushPressedKeys();
}

void AYellPlayer::EndPlay(const EEndPlayReason::Type Reason)
{
	CloseConsole();
	if (Capture)
	{
		Capture->Close();
		Capture.Reset();
	}
	bRecording = false;
	for (const auto& Entry : Requests)
	{
		Entry.Value->OnProcessRequestComplete().Unbind();
		Entry.Value->CancelRequest();
	}
	Requests.Reset();
	ClearAudio(TEXT("partida_cerrada"));
	Super::EndPlay(Reason);
}

bool AYellPlayer::HasVoiceFocus() const
{
	const ULocalPlayer* Local = GetLocalPlayer();
	const FViewport* Viewport = Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
	return Viewport && Viewport->HasFocus();
}

bool AYellPlayer::CanTransmit() const
{
	const AYellCommander* Commander = GetPawn<AYellCommander>();
	const AYellBattle* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	return Commander && Commander->Health() > 0 && Battle && Battle->Winner() == INDEX_NONE;
}

void AYellPlayer::LookX(const float Value) { if (!Console) AddYawInput(Value * 0.42f); }
void AYellPlayer::LookY(const float Value) { if (!Console) AddPitchInput(-Value * 0.42f); }
void AYellPlayer::Jump() { if (CanTransmit()) GetPawn<AYellCommander>()->Jump(); }
void AYellPlayer::ToggleDetails() { bDetails = !bDetails; }
void AYellPlayer::ToggleSpeech()
{
	bVoiceFeedback = !bVoiceFeedback;
	if (!bVoiceFeedback)
	{
		ClearAudio(TEXT("silenciado"));
	}
	Feedback(bVoiceFeedback ? TEXT("Voz de radio activada.") : TEXT("Voz de radio silenciada."), false);
}
void AYellPlayer::ToggleRadio()
{
	if (!bRecording)
	{
		bRadio = !bRadio;
	}
}
void AYellPlayer::ToggleModel()
{
	if (!bRecording)
	{
		Model = AvailableModels[(AvailableModels.IndexOfByKey(Model) + 1) % AvailableModels.Num()];
		const TCHAR* Label = Model == TEXT("A") ? TEXT("Modelo A · BiGRU")
			: Model == TEXT("B") ? TEXT("Modelo B · Qwen local")
			: Model == TEXT("D") ? TEXT("Modelo D · Decisiones") : TEXT("Modelo C · DistilBERT");
		Feedback(Label, false);
	}
}

void AYellPlayer::Reinforce() { AskReinforcement(false); }
void AYellPlayer::ReinforceMedic() { AskReinforcement(true); }

void AYellPlayer::AskReinforcement(const bool bMedical)
{
	if (CanTransmit())
	{
		const FVector Position = GetPawn()->GetActorLocation();
		Feedback(GetWorld()->GetAuthGameMode<AYellBattle>()->TryReinforce(0, bMedical, &Position), true);
	}
}

void AYellPlayer::RestartBattle()
{
	const AYellBattle* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	if (Battle && Battle->Winner() != INDEX_NONE)
	{
		UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
	}
}

void AYellPlayer::OpenConsole()
{
	if (Console || bRecording || !CanTransmit() || !GEngine->GameViewport || !CanQueueRequest())
	{
		return;
	}
	SAssignNew(Console, SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(FMargin(24, 24, 24, 124))
		[
			SNew(SBox).WidthOverride(560)
			[
				SNew(SBorder).BorderBackgroundColor(FLinearColor(.04f, .11f, .13f, 1)).Padding(16)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 7)
					[
						SNew(STextBlock).Text(FText::FromString(bRadio ? TEXT("ORDEN POR RADIO · ENTER PARA ENVIAR")
							: TEXT("ORDEN POR PROXIMIDAD · ENTER PARA ENVIAR")))
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						SAssignNew(ConsoleInput, SEditableTextBox)
						.HintText(FText::FromString(TEXT("Alfa, avancen por el centro")))
						.OnTextCommitted(FOnTextCommitted::CreateUObject(this, &AYellPlayer::Commit))
					]
				]
			]
		];
	GEngine->GameViewport->AddViewportWidgetContent(Console.ToSharedRef(), 20);
	FInputModeGameAndUI Mode;
	Mode.SetWidgetToFocus(ConsoleInput);
	SetInputMode(Mode);
	bShowMouseCursor = true;
}

void AYellPlayer::CloseConsole()
{
	if (Console)
	{
		if (GEngine && GEngine->GameViewport)
		{
			GEngine->GameViewport->RemoveViewportWidgetContent(Console.ToSharedRef());
		}
		Console.Reset();
		ConsoleInput.Reset();
		bShowMouseCursor = false;
		SetInputMode(FInputModeGameOnly());
	}
}

void AYellPlayer::Commit(const FText& Text, const ETextCommit::Type CommitType)
{
	if (CommitType == ETextCommit::OnEnter || CommitType == ETextCommit::OnCleared)
	{
		const FString Message = Text.ToString().TrimStartAndEnd();
		CloseConsole();
		if (CommitType == ETextCommit::OnEnter)
		{
			SubmitText(Message);
		}
	}
}

FYellRequestContext AYellPlayer::MakeContext() const
{
	return { FGuid::NewGuid(), bRadio ? EYellChannel::Radio : EYellChannel::Nearby,
		GetPawn() ? GetPawn()->GetActorLocation() : FVector::ZeroVector, GetWorld()->GetTimeSeconds() };
}

void AYellPlayer::SubmitText(const FString& Message)
{
	if (!Message.IsEmpty() && Message.Len() <= 500 && CanTransmit() && !bRecording && CanQueueRequest())
	{
		Send(Message, {}, MakeContext());
	}
}

#if WITH_DEV_AUTOMATION_TESTS
void AYellPlayer::SubmitTestWave(TArray<uint8> Wave)
{
	if (!Wave.IsEmpty() && CanTransmit() && !bRecording && CanQueueRequest())
	{
		FWaveModInfo Info;
		if (!Info.ReadWaveInfo(Wave.GetData(), Wave.Num()) || *Info.pFormatTag != FWaveModInfo::WAVE_INFO_FORMAT_PCM
			|| *Info.pBitsPerSample != 16 || *Info.pChannels != 1)
		{
			Feedback(TEXT("Fixture WAV de prueba inválida."), false);
			return;
		}
		FYellVoiceBuffer Buffer;
		const int32 Samples = Info.SampleDataSize / sizeof(int16);
		float Packet[512];
		for (int32 First = 0; First < Samples; First += UE_ARRAY_COUNT(Packet))
		{
			const int32 Count = FMath::Min(Samples - First, static_cast<int32>(UE_ARRAY_COUNT(Packet)));
			for (int32 Offset = 0; Offset < Count; ++Offset)
			{
				int16 Sample;
				FMemory::Memcpy(&Sample, Info.SampleDataStart + (First + Offset) * sizeof(int16), sizeof(int16));
				Packet[Offset] = Sample / 32768.0f;
			}
			Buffer.Append(Packet, Count, 1, *Info.pSamplesPerSec, First == 0);
		}
		FYellVoiceTake Take = Buffer.Finish();
		VoiceContext = MakeContext();
		VoiceContext.ReleasedAt = FPlatformTime::Seconds();
		RecordVoiceResult(Take.Stats, Take.Stats.Result(), TEXT("Paquetes de prueba"), Take.Stats.AudioMs());
		if (!Take.Wave.IsEmpty())
		{
			Send(FString(), MoveTemp(Take.Wave), VoiceContext);
		}
	}
}
#endif

void AYellPlayer::StartRecording()
{
	if (bRecording || Console || !CanTransmit() || !CanQueueRequest())
	{
		return;
	}
	VoiceContext = MakeContext();
	CaptureStarted = FPlatformTime::Seconds();
	MicLevel = 0;
	Transcript.Reset();
	DebugJson.Reset();
	Capture = MakeUnique<FYellVoiceDevice>();
	const EYellVoiceResult Result = Capture->Start();
	if (Result != EYellVoiceResult::Ready)
	{
		RecordVoiceResult({}, Result, Capture->GetDeviceName(), 0);
		Capture.Reset();
		return;
	}
	bRecording = true;
	bMicReady = false;
	NextMicUpdate = 0;
	Status = TEXT("Abriendo el micrófono… espera la señal de hablar.");
}

void AYellPlayer::StopRecording()
{
	FinishRecording(!HasVoiceFocus() ? EYellVoiceResult::FocusLost
		: !CanTransmit() ? EYellVoiceResult::Interrupted : EYellVoiceResult::Ready);
}

void AYellPlayer::FinishRecording(EYellVoiceResult Result)
{
	if (!bRecording)
	{
		return;
	}
	bRecording = false;
	VoiceContext.ReleasedAt = FPlatformTime::Seconds();
	const double HeldMs = (VoiceContext.ReleasedAt - CaptureStarted) * 1000;
	if (HeldMs >= FYellVoiceBuffer::MaxSeconds * 1000 && Result == EYellVoiceResult::Ready)
	{
		Result = EYellVoiceResult::TimeLimit;
	}
	FYellVoiceTake Take = Capture->Finish(Result == EYellVoiceResult::Ready);
	if (Result == EYellVoiceResult::Ready)
	{
		Result = Take.Stats.Result();
	}
	RecordVoiceResult(Take.Stats, Result, Capture->GetDeviceName(), HeldMs);
	Capture.Reset();
	MicLevel = 0;
	if (Result == EYellVoiceResult::Ready && !Take.Wave.IsEmpty())
	{
		Send(FString(), MoveTemp(Take.Wave), VoiceContext);
	}
}

void AYellPlayer::RecordVoiceResult(const FYellVoiceStats& Stats, const EYellVoiceResult Result,
	const FString& Device, const double HeldMs)
{
	const TCHAR* Code = YellVoiceCode(Result);
	VoiceDiagnostics = FString::Printf(TEXT("Mic %.2f/%.2f s · %d Hz · %d paquetes · %d cortes · %s"),
		Stats.AudioMs() / 1000, HeldMs / 1000, Stats.Rate, Stats.Packets, Stats.Gaps, Code);
	const TSharedRef<FJsonObject> Record = MakeShared<FJsonObject>();
	Record->SetStringField(TEXT("timestamp_utc"), FDateTime::UtcNow().ToIso8601());
	Record->SetStringField(TEXT("request_id"), VoiceContext.Id.ToString(EGuidFormats::DigitsWithHyphens));
	Record->SetStringField(TEXT("channel"), VoiceContext.Channel == EYellChannel::Radio ? TEXT("radio") : TEXT("proximidad"));
	Record->SetStringField(TEXT("device"), Device);
	Record->SetStringField(TEXT("capture_status"), Code);
	Record->SetNumberField(TEXT("held_ms"), HeldMs);
	Record->SetNumberField(TEXT("audio_ms"), Stats.AudioMs());
	Record->SetNumberField(TEXT("sample_rate_hz"), Stats.Rate);
	Record->SetNumberField(TEXT("channels"), Stats.Channels);
	Record->SetNumberField(TEXT("packets"), Stats.Packets);
	Record->SetNumberField(TEXT("discontinuities"), Stats.Gaps);
	Record->SetBoolField(TEXT("startup_discontinuity"), Stats.bInitialGap);
	Record->SetNumberField(TEXT("peak_dbfs"), Stats.PeakDbfs());
	FString Json;
	FJsonSerializer::Serialize(Record, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
	FFileHelper::SaveStringToFile(Json + TEXT("\n"), *FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("YellVoice.jsonl")),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
	UE_LOG(LogYellVoice, Display, TEXT("%s %s"), *VoiceContext.Id.ToString(), *VoiceDiagnostics);
	if (Result != EYellVoiceResult::Ready)
	{
		Feedback(YellVoiceMessage(Result), true);
	}
}

void AYellPlayer::Send(const FString& Message, TArray<uint8> Wave, const FYellRequestContext& Context)
{
	if (!CanQueueRequest()) return;
	const auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	if (!Battle || Battle->AlliedNames().IsEmpty())
	{
		Feedback(TEXT("No quedan pelotones aliados disponibles."), true);
		return;
	}
	Transcript = Message;
	DebugJson.Reset();
	Status = TEXT("Procesando transmisión local…");
	TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
	const FString Id = Context.Id.ToString(EGuidFormats::DigitsWithHyphens);
	Body->SetStringField(TEXT("request_id"), Id);
	Body->SetStringField(TEXT("model"), Model);
	TArray<TSharedPtr<FJsonValue>> Names;
	for (const FString& Name : Battle->AlliedNames())
	{
		Names.Add(MakeShared<FJsonValueString>(Name));
	}
	Body->SetArrayField(TEXT("squads"), MoveTemp(Names));
	TArray<TSharedPtr<FJsonValue>> Soldiers;
	for (const FString& Name : Battle->AlliedSoldierNames())
	{
		Soldiers.Add(MakeShared<FJsonValueString>(Name));
	}
	Body->SetArrayField(TEXT("soldiers"), MoveTemp(Soldiers));
	if (Model == TEXT("D"))
	{
		const bool bUsingRadio = Context.Channel == EYellChannel::Radio;
		Body->SetBoolField(TEXT("radio"), bUsingRadio);
		auto Roster = MakeShared<FJsonObject>();
		for (const auto& Member : Battle->Units())
		{
			if (!Member.IsValid() || Member->Team != 0 || !Member->IsAlive()) continue;
			auto Entry = MakeShared<FJsonObject>();
			const double Distance = FVector::Dist(Context.Origin,Member->GetActorLocation());
			Entry->SetStringField(TEXT("nombre"),Member->GivenName);
			Entry->SetStringField(TEXT("peloton"),Member->Squad.ToString());
			Entry->SetNumberField(TEXT("distancia"),Distance);
			Entry->SetBoolField(TEXT("disponible"),Member->CanAct() && (bUsingRadio || Distance <= Battle->VoiceRadius()));
			Entry->SetStringField(TEXT("estado"),Member->CanAct() ? TEXT("en servicio") : TEXT("incapacitado"));
			Roster->SetObjectField(Member->CallSign.ToString(),Entry);
		}
		Body->SetObjectField(TEXT("roster"),Roster);
		double Closest = TNumericLimits<double>::Max();
		for (const EYellZone Zone : {EYellZone::Home,EYellZone::Rival,EYellZone::Left,EYellZone::Center,EYellZone::Right})
		{
			const double Distance = FVector::DistSquared2D(Context.Origin,Battle->Position(Zone,0));
			if (Distance < Closest)
			{
				Closest = Distance;
				Body->SetStringField(TEXT("here"),YellOrder::ZoneText(Zone).Replace(TEXT(" "),TEXT("_")));
			}
		}
	}
	Body->SetStringField(Wave.IsEmpty() ? TEXT("text") : TEXT("wav"), Wave.IsEmpty() ? Message : FBase64::Encode(Wave));
	FString Content;
	FJsonSerializer::Serialize(Body, TJsonWriterFactory<>::Create(&Content));
	const FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
	Requests.Add(Context.Id, Request);
	Request->SetURL(TEXT("http://127.0.0.1:18765/v1/interpret"));
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json; charset=utf-8"));
	Request->SetContentAsString(Content);
	Request->SetTimeout(44.0f);
	Request->OnProcessRequestComplete().BindUObject(this, &AYellPlayer::OnResponse, Context, Model, FPlatformTime::Seconds());
	if (!Request->ProcessRequest() && Requests.Remove(Context.Id))
	{
		Feedback(TEXT("No se pudo iniciar la conexión al servicio local."), false);
	}
}

void AYellPlayer::OnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, const bool bSucceeded,
	const FYellRequestContext Context, const FString RequestedModel, const double SentAt)
{
	if (Requests.FindRef(Context.Id) != Request)
	{
		return;
	}
	Requests.Remove(Context.Id);
	const double RealMs = 1000 * (FPlatformTime::Seconds() - SentAt);
	auto LogFailure = [&](const TCHAR* Code)
	{
		FJsonObject Failure;
		Failure.SetStringField(TEXT("request_id"), Context.Id.ToString(EGuidFormats::DigitsWithHyphens));
		Failure.SetStringField(TEXT("model"), RequestedModel);
		Failure.SetStringField(TEXT("error_code"), Code);
		LogResult(Failure, Context, false, RealMs);
	};
	TSharedPtr<FJsonObject> Envelope;
	if (!bSucceeded || !Response || !FJsonSerializer::Deserialize(
		TJsonReaderFactory<>::Create(Response->GetContentAsString()), Envelope) || !Envelope)
	{
		Feedback(TEXT("Servicio NLP sin respuesta. Consulte la terminal local."), true, &Context, SentAt);
		LogFailure(TEXT("sin_respuesta"));
		return;
	}
	FString ReportedId, ReportedModel, Error;
	FGuid ParsedId;
	if (Response->GetResponseCode() != 200)
	{
		Envelope->TryGetStringField(TEXT("error"), Error);
		Feedback(Error.IsEmpty() ? TEXT("El servicio rechazó la transmisión.") : Error.Left(160), true, &Context, SentAt);
		LogFailure(*FString::FromInt(Response->GetResponseCode()));
		return;
	}
	if (!Envelope->TryGetStringField(TEXT("request_id"), ReportedId) || !FGuid::Parse(ReportedId, ParsedId)
		|| ParsedId != Context.Id || !Envelope->TryGetStringField(TEXT("model"), ReportedModel) || ReportedModel != RequestedModel
		|| !CanTransmit())
	{
		Feedback(TEXT("La respuesta llegó fuera de contexto."), false);
		LogFailure(TEXT("fuera_de_contexto"));
		return;
	}
	Envelope->TryGetStringField(TEXT("transcript"), Transcript);
	Transcript = Transcript.Left(500);
	double STT = 0, NLP = 0;
	Envelope->TryGetNumberField(TEXT("stt_ms"), STT);
	Envelope->TryGetNumberField(TEXT("nlp_ms"), NLP);
	const double ReleasedMs = Context.ReleasedAt > 0 ? 1000 * (FPlatformTime::Seconds() - Context.ReleasedAt) : RealMs;
	StageTiming = FString::Printf(TEXT("STT %.0f ms · Decisión %.0f ms · Respuesta %.0f ms"), STT, NLP, ReleasedMs);
	DebugJson.Reset();
	const TSharedPtr<FJsonObject>* TimedDialogue = nullptr;
	if (Envelope->TryGetObjectField(TEXT("dialogue"), TimedDialogue) && TimedDialogue && TimedDialogue->IsValid())
	{
		double Generation = 0, Synthesis = 0;
		(*TimedDialogue)->TryGetNumberField(TEXT("generation_ms"), Generation);
		(*TimedDialogue)->TryGetNumberField(TEXT("tts_ms"), Synthesis);
		StageTiming = FString::Printf(TEXT("STT %.0f · Dec. %.0f · Charla %.0f · TTS %.0f · Total %.0f ms"),
			STT, NLP, Generation, Synthesis, ReleasedMs);
	}
	const TSharedPtr<FJsonObject>* Proposed = nullptr;
	if ((Envelope->TryGetObjectField(TEXT("decision"), Proposed) || Envelope->TryGetObjectField(TEXT("prediction"), Proposed))
		&& Proposed && Proposed->IsValid())
	{
		FJsonSerializer::Serialize(Proposed->ToSharedRef(), TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&DebugJson));
	}
	const TSharedPtr<FJsonObject>* Validated = nullptr;
	FString Reason;
	FYellOrder Order;
	bool bAccepted = false;
	const bool bValid = Envelope->TryGetObjectField(TEXT("command"), Validated) && Validated && Validated->IsValid()
		&& YellOrder::Parse(**Validated, Order, Reason);
	if (bValid)
	{
		const TSharedPtr<FJsonObject>* Talk = nullptr;
		if (Order.Intent == EYellIntent::Chat && Envelope->TryGetObjectField(TEXT("dialogue"), Talk) && Talk && Talk->IsValid())
		{
			FString Speaker, Line, Encoded;
			(*Talk)->TryGetStringField(TEXT("speaker_id"), Speaker);
			(*Talk)->TryGetStringField(TEXT("text"), Line);
			auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
			AYellSoldier* Source = nullptr;
			const bool bLocal = Context.Channel == EYellChannel::Nearby;
			for (const auto& Unit : Battle->Units())
			{
				if (Unit.IsValid() && Unit->Team == 0 && Unit->CanAct() && Unit->CallSign.ToString() == Speaker
					&& (!bLocal || FVector::Dist(GetPawn()->GetActorLocation(),Unit->GetActorLocation()) <= Battle->VoiceRadius()))
				{
					Source = Unit.Get();
					break;
				}
			}
			Feedback(Source ? Source->GivenName + TEXT(": ") + Line.Left(220) : TEXT("Ningún interlocutor disponible."), false);
			Recent.Insert(Status, 0);
			Recent.SetNum(FMath::Min(5, Recent.Num()));
			if (Source && bVoiceFeedback && GetWorld()->GetAudioDeviceRaw() && (*Talk)->TryGetStringField(TEXT("pcm"),Encoded))
			{
				TArray<uint8> PCM;
				double Rate = 0;
				if (Encoded.Len() <= 2400000 && (*Talk)->TryGetNumberField(TEXT("rate"),Rate) && Rate == 24000
					&& FBase64::Decode(Encoded,PCM) && PCM.Num() > 0 && PCM.Num() % 2 == 0)
				{
					FAudioReply Reply;
					Reply.RequestId = Context.Id;
					Reply.InputAt = Context.ReleasedAt > 0 ? Context.ReleasedAt : SentAt;
					Reply.Speaker = Source;
					Reply.bSpatial = bLocal;
					Reply.Duration = PCM.Num() / 48000.f;
					Reply.PCM = MoveTemp(PCM);
					(*Talk)->SetBoolField(TEXT("audio_queued"), true);
					(*Talk)->SetNumberField(TEXT("audio_ms"), Reply.Duration * 1000);
					QueueAudio(MoveTemp(Reply));
				}
			}
			(*Talk)->RemoveField(TEXT("pcm"));
			LogResult(*Envelope, Context, false, RealMs);
			return;
		}
		FString ServiceReason;
		Envelope->TryGetStringField(TEXT("reason"), ServiceReason);
		Reason = GetWorld()->GetAuthGameMode<AYellBattle>()->Dispatch(Order, Context, bAccepted);
		if (Order.Intent == EYellIntent::Unknown && !ServiceReason.IsEmpty())
		{
			Reason = ServiceReason.Left(180);
		}
	}
	Feedback(Reason.IsEmpty() ? TEXT("La respuesta no cumple el contrato de órdenes.") : Reason, true, &Context, SentAt);
	LogResult(*Envelope, Context, bAccepted, RealMs);
}

void AYellPlayer::Feedback(const FString& Message, const bool bSpeak, const FYellRequestContext* Context, const double SentAt)
{
	Status = Message;
	if (bSpeak)
	{
		Recent.Insert(Message, 0);
		Recent.SetNum(FMath::Min(5, Recent.Num()));
	}
	if (bSpeak && bVoiceFeedback && GetWorld()->GetAudioDeviceRaw())
	{
		const bool bAcknowledged = Message.StartsWith(TEXT("¡Copiado")) ||
			Message.StartsWith(TEXT("Refuerzos en camino")) || Message.StartsWith(TEXT("Canal de charla"));
		USoundBase* Cue = Message.StartsWith(TEXT("¡Por usted")) ? MoraleCue.Get()
			: bAcknowledged ? AcknowledgeCue.Get() : ClarifyCue.Get();
		if (Cue)
		{
			FAudioReply Reply;
			Reply.Cue = Cue;
			if (Context)
			{
				Reply.RequestId = Context->Id;
				Reply.InputAt = Context->ReleasedAt > 0 ? Context->ReleasedAt : SentAt;
			}
			QueueAudio(MoveTemp(Reply));
		}
	}
}

bool AYellPlayer::CanQueueRequest()
{
	if (PendingRequests() + PendingAudio() < MaxPending)
	{
		return true;
	}
	Feedback(TEXT("Radio llena. Hay cuatro solicitudes o audios pendientes."), false);
	return false;
}

void AYellPlayer::QueueAudio(FAudioReply Reply)
{
	if (!Reply.RequestId.IsValid() && PendingRequests() + PendingAudio() >= MaxPending) return;
	Reply.QueuedAt = FPlatformTime::Seconds();
	LogAudio(Reply, TEXT("en_cola"), Reply.QueuedAt);
	AudioQueue.Add(MoveTemp(Reply));
}

void AYellPlayer::UpdateAudio()
{
	const double Now = FPlatformTime::Seconds();
	if (PlayingReply)
	{
		const bool bProceduralDone = PlayingVoice.IsValid() && PlayingVoice->GetAvailableAudioByteCount() == 0
			&& Now - PlaybackStarted >= PlayingReply->Duration + .15;
		if (!bProceduralDone && CurrentReply.IsValid() && CurrentReply->IsPlaying())
		{
			return;
		}
		if (CurrentReply.IsValid()) CurrentReply->Stop();
		LogAudio(*PlayingReply, TEXT("finalizado"), Now);
		PlayingReply.Reset();
		CurrentReply.Reset();
		PlayingVoice.Reset();
	}
	if (bRecording || !bVoiceFeedback || AudioQueue.IsEmpty())
	{
		return;
	}
	FAudioReply Reply = MoveTemp(AudioQueue[0]);
	AudioQueue.RemoveAt(0);
	if (Reply.Cue.IsValid())
	{
		CurrentReply = UGameplayStatics::SpawnSound2D(this, Reply.Cue.Get(), 0.66f);
	}
	else if (const auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>(); Battle
		&& !Reply.PCM.IsEmpty() && (!Reply.bSpatial || (Reply.Speaker.IsValid() && Reply.Speaker->CanAct()
		&& GetPawn() && FVector::Dist(GetPawn()->GetActorLocation(), Reply.Speaker->GetActorLocation())
			<= Battle->VoiceRadius())))
	{
		auto* Voice = NewObject<USoundWaveProcedural>(this);
		Voice->SetSampleRate(24000);
		Voice->NumChannels = 1;
		Voice->Duration = Reply.Duration;
		Voice->QueueAudio(Reply.PCM.GetData(), Reply.PCM.Num());
		PlayingVoice = Voice;
		auto* Attenuation = Reply.bSpatial ? NewObject<USoundAttenuation>(this) : nullptr;
		CurrentReply = Reply.bSpatial ? UGameplayStatics::SpawnSoundAttached(Voice, Reply.Speaker->GetRootComponent(),
			NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, false, 1.f, 1.f, 0.f, Attenuation)
			: UGameplayStatics::SpawnSound2D(this, Voice);
		Reply.PCM.Empty();
	}
	if (CurrentReply.IsValid())
	{
		PlaybackStarted = FPlatformTime::Seconds();
		LogAudio(Reply, TEXT("iniciado"), PlaybackStarted);
		PlayingReply = MoveTemp(Reply);
	}
	else
	{
		PlayingVoice.Reset();
		LogAudio(Reply, TEXT("omitido"), Now);
	}
}

void AYellPlayer::ClearAudio(const TCHAR* Event)
{
	const double Now = FPlatformTime::Seconds();
	if (CurrentReply.IsValid()) CurrentReply->Stop();
	CurrentReply.Reset();
	PlayingVoice.Reset();
	if (PlayingReply) LogAudio(*PlayingReply, Event, Now);
	PlayingReply.Reset();
	for (const FAudioReply& Reply : AudioQueue) LogAudio(Reply, Event, Now);
	AudioQueue.Reset();
}

void AYellPlayer::LogAudio(const FAudioReply& Reply, const TCHAR* Event, const double Now) const
{
	if (!Reply.RequestId.IsValid()) return;
	auto Line = MakeShared<FJsonObject>();
	Line->SetStringField(TEXT("request_id"), Reply.RequestId.ToString(EGuidFormats::DigitsWithHyphens));
	Line->SetStringField(TEXT("timestamp_utc"), FDateTime::UtcNow().ToIso8601());
	Line->SetStringField(TEXT("event"), Event);
	Line->SetNumberField(TEXT("since_queued_ms"), 1000 * (Now - Reply.QueuedAt));
	Line->SetNumberField(TEXT("since_input_ms"), 1000 * (Now - Reply.InputAt));
	FString Data;
	FJsonSerializer::Serialize(Line, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));
	FFileHelper::SaveStringToFile(Data + TEXT("\n"), *FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("YellAudio.jsonl")),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
}

void AYellPlayer::LogResult(const FJsonObject& Envelope, const FYellRequestContext& Context, const bool bAccepted, const double RealMs)
{
	const TSharedRef<FJsonObject> Line = MakeShared<FJsonObject>(Envelope);
	Line->SetStringField(TEXT("timestamp_utc"), FDateTime::UtcNow().ToIso8601());
	Line->SetStringField(TEXT("channel"), Context.Channel == EYellChannel::Radio ? TEXT("radio") : TEXT("proximidad"));
	Line->SetStringField(TEXT("result"), Status);
	Line->SetBoolField(TEXT("accepted"), bAccepted);
	Line->SetNumberField(TEXT("round_trip_ms"), RealMs);
	if (Context.ReleasedAt > 0)
	{
		Line->SetNumberField(TEXT("release_to_feedback_ms"), 1000 * (FPlatformTime::Seconds() - Context.ReleasedAt));
	}
	FString Data;
	FJsonSerializer::Serialize(Line, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));
	FFileHelper::SaveStringToFile(Data + TEXT("\n"), *FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("YellOrders.jsonl")),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
}
