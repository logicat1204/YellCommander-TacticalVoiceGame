#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "YellOrder.h"
#include "YellReinforcements.h"
#include "YellBattle.generated.h"

class AStaticMeshActor;
class UBoxComponent;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class ATextRenderActor;

enum class EYellSoldierState : uint8
{
	Idle, FollowingOrder, Moving, TakingCover, Attacking, Defending, Retreating, Healing, Downed, Dead
};

UCLASS()
class AYellNavigationBounds : public ANavMeshBoundsVolume
{
	GENERATED_BODY()

public:
	AYellNavigationBounds(const FObjectInitializer& Initializer);
};

UCLASS()
class AYellSoldier : public ACharacter
{
	GENERATED_BODY()

public:
	AYellSoldier();
	void Initialize(uint8 InTeam, FName InSquad, int32 Index, bool bInMedic);
	void Accept(const FYellOrder& Order, const FVector& Goal, const FVector& Alternate);
	void Step(class AYellBattle& Battle, double Time);
	void Hurt(float Damage, double Time);
	void Treat(double Time);
	bool CanAct() const;
	bool IsAlive() const { return State != EYellSoldierState::Dead; }
	FVector Eye() const;

	uint8 Team = 0;
	FName Squad;
	FName CallSign;
	FString GivenName;
	bool bMedic = false;
	float Health = 100.0f;
	double BoostUntil = 0.0;
	EYellSoldierState State = EYellSoldierState::Idle;
	FYellOrder CurrentOrder;
	FVector Destination = FVector::ZeroVector;
	AYellSoldier* LastSeenOpponent() const { return VisibleOpponent.Get(); }

private:
	void Move(const FVector& Goal, double Time, float Acceptance = 65.0f);
	void Stop();
	void UpdateVisuals();

	UPROPERTY() TObjectPtr<UStaticMeshComponent> Torso;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Helmet;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Visor;
	TWeakObjectPtr<AYellSoldier> VisibleOpponent;
	FVector Secondary = FVector::ZeroVector;
	FVector LastMoveGoal = FVector::ZeroVector;
	double NextMove = 0.0;
	double NextAction = 0.0;
	double DownUntil = 0.0;
	double CoverUntil = 0.0;
	FVector CoverGoal = FVector::ZeroVector;
	bool bAlternate = false;
};

struct FYellSquad
{
	FName Id;
	uint8 Team = 0;
	bool bMedic = false;
	TArray<TWeakObjectPtr<AYellSoldier>> Members;

	int32 Alive() const;
	int32 Ready() const;
};

DECLARE_MULTICAST_DELEGATE_TwoParams(FYellTacticalEvent, const FYellOrder&, const TArray<AYellSoldier*>&);

UCLASS()
class AYellBattle : public AGameModeBase
{
	GENERATED_BODY()

public:
	AYellBattle();
	virtual void BeginPlay() override;
	virtual void RestartPlayer(AController* NewPlayer) override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	FString Dispatch(FYellOrder Order, const FYellRequestContext& Context, bool& bAccepted);
	FString TryReinforce(uint8 Team, bool bMedical, const FVector* Requester = nullptr);
	TArray<FString> AlliedNames() const;
	TArray<FString> AlliedSoldierNames() const;
	FVector Position(EYellZone Zone, uint8 Team) const;
	FVector SpawnPosition(uint8 Team) const;
	FVector CorePosition(uint8 Team) const;
	float CoreHealth(uint8 Team) const { return BaseHealth[Team]; }
	float NextReinforcement(uint8 Team) const;
	float NextMorale() const;
	int32 Winner() const { return WinningTeam; }
	void DamageCore(uint8 Team, float Damage);
	void SimulatePulse(AYellSoldier& Soldier, AActor* Target, const FVector& Point);
	bool Visible(const AYellSoldier& Observer, const AActor& Target, const FVector& Point, bool bCone = true) const;
	AYellSoldier* FindOpponent(AYellSoldier& Soldier) const;
	AYellSoldier* FindPatient(const AYellSoldier& Medic) const;
	bool FindCover(const AYellSoldier& Soldier, const AActor& Threat, FVector& Goal) const;
	const TArray<FYellSquad>& Roster() const { return Squads; }
	const TArray<TWeakObjectPtr<AYellSoldier>>& Units() const { return AllUnits; }
	bool DetectedByPlayer(const AYellSoldier& Soldier) const;
	bool IsTerminalNearby(uint8 Team, const FVector& Location) const;
	float VoiceRadius() const { return NearbyRadius; }
	FString RivalPersonality() const;

	FYellTacticalEvent OnOrder;

private:
	struct FContact
	{
		FName Squad;
		EYellZone Lane = EYellZone::Center;
		double Reported = 0.0;
		float Confidence = 0.0f;
	};

	struct FScoutReport
	{
		FContact Contact;
		double SendAt = 0.0;
	};

	void BuildArena();
	void UpdateBattle();
	void RunRival(double Now);
	void ReportContact(const FContact& Contact);
	bool SpawnSquad(uint8 Team, FName Name, bool bMedic, int32 Count);
	void ApplyOrder(const FYellOrder& Order, const TArray<AYellSoldier*>& Recipients);
	AStaticMeshActor* Block(const FVector& Location, const FVector& Size, const FLinearColor& Tint,
		bool bCollision = true, bool bRound = false);
	void Sign(const FVector& Location, const FString& Text, const FColor& Color, float Size, float Yaw = 180.0f);
	EYellZone LaneOf(const FVector& Location) const;

	TArray<FYellSquad> Squads;
	TArray<TWeakObjectPtr<AYellSoldier>> AllUnits;
	TArray<FVector> CoverPositions;
	TMap<FGuid, double> SeenRequests;
	TMap<FName, FContact> Intelligence;
	TMap<TWeakObjectPtr<AYellSoldier>, FScoutReport> PendingReports;
	TMap<TWeakObjectPtr<AYellSoldier>, double> PlayerIntel;
	FTimerHandle BattleTimer;
	FDelegateHandle OrderListener;
	TWeakObjectPtr<AStaticMeshActor> Cores[2];
	FYellReinforcements Reinforcements[2];
	float BaseHealth[2] = {500.0f, 500.0f};
	double MoraleReady = 0.0;
	double NextRivalDecision = 0.0;
	int32 Personality = 0;
	int32 Tactic = 0;
	int32 WinningTeam = INDEX_NONE;
	bool bArenaReady = false;

	UPROPERTY(EditDefaultsOnly, Category="Yell|Radio") float NearbyRadius = 850.0f;
	UPROPERTY(EditDefaultsOnly, Category="Yell|Gameplay") float ReinforcementCooldown = 120.0f;
	UPROPERTY(EditDefaultsOnly, Category="Yell|Gameplay") float MoraleDuration = 18.0f;
	UPROPERTY(EditDefaultsOnly, Category="Yell|Gameplay") float MoraleCooldown = 50.0f;
};
