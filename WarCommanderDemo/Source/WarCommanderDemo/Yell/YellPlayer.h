#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "Interfaces/IHttpRequest.h"
#include "YellOrder.h"
#include "YellVoice.h"
#include "YellPlayer.generated.h"

class FJsonObject;
class SWidget;
class SEditableTextBox;
class UAudioComponent;
class UCameraComponent;
class USoundBase;
class USoundWaveProcedural;
class AYellSoldier;

UCLASS()
class AYellCommander : public ACharacter
{
	GENERATED_BODY()

public:
	AYellCommander();
	void Hurt(float Damage);
	float Health() const { return HitPoints; }

private:
	void Recover();
	UPROPERTY() TObjectPtr<UCameraComponent> View;
	FTimerHandle RespawnTimer;
	float HitPoints = 100.0f;
};

UCLASS()
class AYellPlayer : public APlayerController
{
	GENERATED_BODY()

public:
	AYellPlayer();
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float DeltaTime) override;
	virtual void FlushPressedKeys() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	FString Status = TEXT("Radio en espera, mi General.");
	FString Transcript;
	FString DebugJson;
	FString StageTiming;
	FString VoiceDiagnostics;
	float MicLevel = 0;
	TArray<FString> Recent;
	FString Model = TEXT("A");
	bool bRadio = true;
	bool bDetails = false;
	bool bRecording = false;
	bool bMicReady = false;
	bool bVoiceFeedback = true;
	static constexpr int32 MaxPending = 4;
	int32 PendingRequests() const { return Requests.Num(); }
	int32 PendingAudio() const { return AudioQueue.Num() + (PlayingReply.IsSet() ? 1 : 0); }
	void SubmitText(const FString& Message);
#if WITH_DEV_AUTOMATION_TESTS
	void SubmitTestWave(TArray<uint8> Wave);
#endif

private:
	void LookX(float Value);
	void LookY(float Value);
	void Jump();
	void ToggleRadio();
	void ToggleModel();
	void ToggleDetails();
	void ToggleSpeech();
	void Reinforce();
	void ReinforceMedic();
	void AskReinforcement(bool bMedical);
	void RestartBattle();
	void OpenConsole();
	void CloseConsole();
	void Commit(const FText& Text, ETextCommit::Type CommitType);
	void StartRecording();
	void StopRecording();
	void FinishRecording(EYellVoiceResult Cancellation);
	bool HasVoiceFocus() const;
	void RecordVoiceResult(const FYellVoiceStats& Stats, EYellVoiceResult Result, const FString& Device, double HeldMs);
	void Send(const FString& Message, TArray<uint8> Wave, const FYellRequestContext& Context);
	void OnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSucceeded, FYellRequestContext Context,
		FString RequestedModel, double SentAt);
	void Feedback(const FString& Message, bool bSpeak, const FYellRequestContext* Context = nullptr, double SentAt = 0);
	void LogResult(const FJsonObject& Envelope, const FYellRequestContext& Context, bool bAccepted, double RealMs);
	FYellRequestContext MakeContext() const;
	bool CanTransmit() const;

	TUniquePtr<FYellVoiceDevice> Capture;
	double CaptureStarted = 0;
	double NextMicUpdate = 0;
	FYellRequestContext VoiceContext;
	TArray<FString> AvailableModels = { TEXT("A"), TEXT("B") };
	TMap<FGuid, FHttpRequestPtr> Requests;
	TSharedPtr<SWidget> Console;
	TSharedPtr<SEditableTextBox> ConsoleInput;
	TWeakObjectPtr<UAudioComponent> CurrentReply;
	TWeakObjectPtr<USoundWaveProcedural> PlayingVoice;
	struct FAudioReply
	{
		FGuid RequestId;
		double InputAt = 0;
		double QueuedAt = 0;
		float Duration = 0;
		bool bSpatial = false;
		TWeakObjectPtr<AYellSoldier> Speaker;
		TWeakObjectPtr<USoundBase> Cue;
		TArray<uint8> PCM;
	};
	TArray<FAudioReply> AudioQueue;
	TOptional<FAudioReply> PlayingReply;
	double PlaybackStarted = 0;
	void QueueAudio(FAudioReply Reply);
	void UpdateAudio();
	void ClearAudio(const TCHAR* Event);
	void LogAudio(const FAudioReply& Reply, const TCHAR* Event, double Now) const;
	bool CanQueueRequest();
	UPROPERTY() TObjectPtr<USoundBase> AcknowledgeCue;
	UPROPERTY() TObjectPtr<USoundBase> ClarifyCue;
	UPROPERTY() TObjectPtr<USoundBase> MoraleCue;
};

UCLASS()
class AYellHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
