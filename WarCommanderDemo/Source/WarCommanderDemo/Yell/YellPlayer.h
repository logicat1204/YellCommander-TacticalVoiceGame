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
class USceneComponent;
class USoundBase;
class USoundWaveProcedural;
class UTexture2D;
class AYellSoldier;
enum class EYellDifficulty : uint8;
enum class EYellEquipment : uint8 { None, Radio, Binoculars };

UCLASS()
class AYellCommander : public ACharacter
{
	GENERATED_BODY()

public:
	AYellCommander();
	void Hurt(float Damage);
	float Health() const { return HitPoints; }
	void UpdateEquipment(EYellEquipment Requested, float DeltaTime);
	void ResetEquipment();
	float OpticBlend() const { return Optics; }

private:
#if WITH_DEV_AUTOMATION_TESTS
	friend class FYellEquipmentFlow;
#endif
	virtual void BeginPlay() override;
	void BuildEquipmentModels();
	void Recover();
	UPROPERTY() TObjectPtr<UCameraComponent> View;
	UPROPERTY() TObjectPtr<USceneComponent> RadioModel;
	UPROPERTY() TObjectPtr<USceneComponent> BinocularModel;
	FTimerHandle RespawnTimer;
	float HitPoints = 100.0f;
	float EquipmentLift = 0.f;
	float Optics = 0.f;
	EYellEquipment ActiveEquipment = EYellEquipment::None;
	static constexpr float StandardFOV = 94.f;
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
	bool bRadio = true;
	bool bDetails = false;
	bool bRecording = false;
	bool bMicReady = false;
	bool bVoiceFeedback = true;
	static constexpr int32 MaxPending = 4;
	int32 PendingRequests() const { return Requests.Num(); }
	int32 PendingAudio() const { return AudioQueue.Num() + (PlayingReply.IsSet() ? 1 : 0); }
	void SubmitText(const FString& Message);
	bool HasMenu() const { return MenuView.IsValid(); }
#if WITH_DEV_AUTOMATION_TESTS
	void SubmitTestWave(TArray<uint8> Wave);
#endif

private:
#if WITH_DEV_AUTOMATION_TESTS
	friend class FYellMenuFlow;
	friend class FYellEquipmentFlow;
#endif
	enum class EMenuPage : uint8 { Main, Difficulty, Settings, Controls, Graphics, Audio, Pause, Result };
	void ShowMenu(EMenuPage Page);
	void CloseMenu();
	void BackFromMenu();
	void EscapeMenu();
	void StartMatch(EYellDifficulty Difficulty);
	void ReturnToMenu();
	void LoadMenuPreferences();
	EMenuPage MenuPage = EMenuPage::Main;
	TSharedPtr<SWidget> MenuView;
	float Sensitivity = .42f;
	bool bMenuTransition = false;
	TArray<TFunction<void()>> PausedResponses;
	void LookX(float Value);
	void LookY(float Value);
	void Jump();
	void ToggleRadio();
	void ToggleDetails();
	void ToggleSpeech();
	void Reinforce();
	void ReinforceMedic();
	void AskReinforcement(bool bMedical);
	void ReturnAfterBattle();
	void OpenConsole();
	void CloseConsole();
	void Commit(const FText& Text, ETextCommit::Type CommitType);
	void StartRecording();
	void StopRecording();
	void FinishRecording(EYellVoiceResult Cancellation);
	void RaiseBinoculars();
	void LowerBinoculars();
	void ResetEquipmentInput();
	float LookScale() const;
	bool HasVoiceFocus() const;
	void RecordVoiceResult(const FYellVoiceStats& Stats, EYellVoiceResult Result, const FString& Device, double HeldMs);
	void Send(const FString& Message, TArray<uint8> Wave, const FYellRequestContext& Context);
	void OnResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSucceeded, FYellRequestContext Context,
		double SentAt);
	void Feedback(const FString& Message, bool bSpeak, const FYellRequestContext* Context = nullptr, double SentAt = 0);
	void LogResult(const FJsonObject& Envelope, const FYellRequestContext& Context, bool bAccepted, double RealMs);
	FYellRequestContext MakeContext() const;
	bool CanTransmit() const;

	TUniquePtr<FYellVoiceDevice> Capture;
	bool bTalkHeld = false;
	bool bBinocularsHeld = false;
	double CaptureStarted = 0;
	double NextMicUpdate = 0;
	FYellRequestContext VoiceContext;
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
		bool bRadioSpatial = false;
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
	UPROPERTY() TObjectPtr<USoundBase> RadioSendCue;
};

UCLASS()
class AYellHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawBinocularView(float Opacity);
	UPROPERTY() TMap<FName, TObjectPtr<UTexture2D>> HUDTextures;
};
