#include "YellBattle.h"

#include "Algo/Count.h"
#include "DrawDebugHelpers.h"
#include "Engine/StaticMeshActor.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "YellPlayer.h"

DEFINE_LOG_CATEGORY_STATIC(LogYellBattle, Log, All);

namespace
{
	constexpr double RequestLifetime = 48.0;
	constexpr double IntelLifetime = 26.0;
	constexpr float PulseReach = 1720.0f;
	constexpr float HearingReach = 1080.0f;

	FVector FormationOffset(const int32 Index, const uint8 Team)
	{
		return FVector((Team == 0 ? -1.0 : 1.0) * (Index % 2) * 125, (Index - 2) * 123, 0);
	}
}

int32 FYellSquad::Alive() const
{
	return Algo::CountIf(Members, [](const auto& Unit) { return Unit.IsValid() && Unit->IsAlive(); });
}

int32 FYellSquad::Ready() const
{
	return Algo::CountIf(Members, [](const auto& Unit) { return Unit.IsValid() && Unit->CanAct(); });
}

AYellBattle::AYellBattle()
{
	PlayerControllerClass = AYellPlayer::StaticClass();
	DefaultPawnClass = AYellCommander::StaticClass();
	HUDClass = AYellHUD::StaticClass();
}

void AYellBattle::BeginPlay()
{
	Super::BeginPlay();
	BuildArena();
	SpawnSquad(0, TEXT("Alfa"), false, 4);
	SpawnSquad(0, TEXT("Bravo"), false, 4);
	SpawnSquad(0, TEXT("Médico"), true, 2);
	SpawnSquad(1, TEXT("Óxido"), false, 3);
	SpawnSquad(1, TEXT("Chispa"), false, 3);
	SpawnSquad(1, TEXT("Resorte"), false, 3);
	Personality = FMath::RandRange(0, 2);
	Tactic = Personality == 0 ? 2 : Personality == 1 ? 4 : 3;
	NextRivalDecision = GetWorld()->GetTimeSeconds() + 6.0;
	OrderListener = OnOrder.AddUObject(this, &AYellBattle::ApplyOrder);
	bArenaReady = true;
	GetWorldTimerManager().SetTimer(BattleTimer, this, &AYellBattle::UpdateBattle, 0.24f, true);
	UE_LOG(LogYellBattle, Display, TEXT("Valle Alfa listo. %d pelotones y %d unidades."), Squads.Num(), AllUnits.Num());
}

void AYellBattle::EndPlay(const EEndPlayReason::Type Reason)
{
	GetWorldTimerManager().ClearTimer(BattleTimer);
	OnOrder.Remove(OrderListener);
	Super::EndPlay(Reason);
}

void AYellBattle::RestartPlayer(AController* NewPlayer)
{
	if (NewPlayer && !NewPlayer->GetPawn())
	{
		RestartPlayerAtTransform(NewPlayer, FTransform(FRotator::ZeroRotator, SpawnPosition(0)));
	}
}

bool AYellBattle::SpawnSquad(const uint8 Team, const FName Name, const bool bMedic, const int32 Count)
{
	if (Count < 1 || Count > FYellReinforcements::MaxMembers || Name.IsNone()
		|| Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; }) >= FYellReinforcements::MaxSquads
		|| Squads.ContainsByPredicate([Team, Name, bMedic](const FYellSquad& S)
			{ return S.Team == Team && S.Alive() > 0 && (S.Id == Name || (bMedic && S.bMedic)); }))
	{
		return false;
	}
	const double Sign = Team == 0 ? -1.0 : 1.0;
	const int32 TeamCount = Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; });
	const FVector Rally(Sign * (TeamCount < 3 ? 2470 : 2220), (TeamCount % 3 - 1) * 920, 94);
	FYellSquad Squad;
	Squad.Id = Name;
	Squad.Team = Team;
	Squad.bMedic = bMedic;
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		AYellSoldier* Unit = GetWorld()->SpawnActor<AYellSoldier>(Rally + FormationOffset(Index, Team),
			FRotator(0, Team == 0 ? 0 : 180, 0), Params);
		if (Unit)
		{
			Unit->Initialize(Team, Name, Index, bMedic);
			Squad.Members.Add(Unit);
			AllUnits.Add(Unit);
		}
	}
	if (Squad.Members.IsEmpty())
	{
		return false;
	}
	Squads.Add(MoveTemp(Squad));
	return true;
}

TArray<FString> AYellBattle::AlliedNames() const
{
	TArray<FString> Names;
	for (const FYellSquad& Squad : Squads)
	{
		if (Squad.Team == 0 && Squad.Alive() > 0)
		{
			Names.Add(Squad.Id.ToString());
		}
	}
	return Names;
}

TArray<FString> AYellBattle::AlliedSoldierNames() const
{
	TArray<FString> Names;
	for (const auto& Unit : AllUnits)
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->IsAlive())
		{
			Names.Add(Unit->CallSign.ToString());
		}
	}
	return Names;
}

FString AYellBattle::Dispatch(FYellOrder Order, const FYellRequestContext& Context, bool& bAccepted)
{
	bAccepted = false;
	const double Now = GetWorld()->GetTimeSeconds();
	if (!bArenaReady || WinningTeam != INDEX_NONE)
	{
		return TEXT("La partida no admite nuevas órdenes.");
	}
	if (!Context.Id.IsValid() || Context.Started > Now + 0.1 || Now - Context.Started > RequestLifetime
		|| SeenRequests.Contains(Context.Id))
	{
		return TEXT("La transmisión ya fue procesada o venció.");
	}
	SeenRequests.Add(Context.Id, Now);
	if (Order.Intent == EYellIntent::Chat)
	{
		return TEXT("Canal de charla. Los pelotones siguen en lo suyo.");
	}
	if (Order.Intent == EYellIntent::Unknown)
	{
		return TEXT("No se entendió la instrucción. Repítala, mi General.");
	}
	const uint8 Team = Context.Channel == EYellChannel::Rival ? 1 : 0;
	const bool bMorale = Order.Intent == EYellIntent::Morale;
	if (!bMorale && (Order.Action == EYellAction::None
		|| (Order.Squad.IsNone() && Order.Soldier.IsNone() && Context.Channel != EYellChannel::Nearby)))
	{
		return TEXT("Indique una acción y un pelotón, mi General.");
	}
	if (!bMorale && (YellOrder::NeedsZone(Order.Action) && Order.Zone == EYellZone::None))
	{
		return TEXT("¿A qué zona nos dirigimos, mi General?");
	}
	if ((Order.Action == EYellAction::Hold || Order.Action == EYellAction::Cancel) && Order.Zone != EYellZone::None)
	{
		return TEXT("Mantener o cancelar se aplica al sitio actual del pelotón.");
	}
	TArray<AYellSoldier*> Recipients;
	TSet<FName> SquadIds;
	bool bRecipientExists = Order.Squad.IsNone() && Order.Soldier.IsNone();
	for (const FYellSquad& Squad : Squads)
	{
		if (Squad.Team != Team || (!Order.Squad.IsNone() && Squad.Id != Order.Squad) || !Squad.Alive())
		{
			continue;
		}
		bRecipientExists |= Order.Soldier.IsNone();
		for (const auto& Member : Squad.Members)
		{
			if (!Member.IsValid() || !Member->IsAlive() || (!Order.Soldier.IsNone() && Member->CallSign != Order.Soldier))
			{
				continue;
			}
			bRecipientExists = true;
			if (Member->CanAct() && (Context.Channel != EYellChannel::Nearby
				|| FVector::DistSquared(Context.Origin, Member->GetActorLocation()) <= FMath::Square(NearbyRadius)))
			{
				Recipients.Add(Member.Get());
				SquadIds.Add(Squad.Id);
			}
		}
	}
	if (Recipients.IsEmpty())
	{
		return bRecipientExists ? TEXT("Ningún soldado disponible recibió la transmisión.")
			: TEXT("El destinatario indicado no está activo.");
	}
	if (!bMorale && SquadIds.Num() != 1)
	{
		return TEXT("Hay varios pelotones al alcance. Indique uno.");
	}
	if (bMorale)
	{
		if (Now < MoraleReady)
		{
			return TEXT("La tropa todavía está recuperando el aliento.");
		}
		MoraleReady = Now + MoraleCooldown;
		bAccepted = true;
		OnOrder.Broadcast(Order, Recipients);
		return FString::Printf(TEXT("¡Por usted y por el almuerzo! Moral para %d soldados."), Recipients.Num());
	}
	Order.Squad = Recipients[0]->Squad;
	if (YellOrder::IsMedical(Order.Action) && !Recipients[0]->bMedic)
	{
		return TEXT("Se requiere un pelotón médico para esa orden.");
	}
	if (Recipients[0]->bMedic && Order.Action == EYellAction::Attack)
	{
		return TEXT("El pelotón médico se dedica a atender a los heridos.");
	}
	if (!Order.Target.IsNone() && !Squads.ContainsByPredicate([&](const FYellSquad& Squad)
		{ return Squad.Team == Team && Squad.Id == Order.Target && Squad.Id != Order.Squad && Squad.Alive() > 0; }))
	{
		return TEXT("El pelotón a atender no está disponible.");
	}
	if (!Order.TargetSoldier.IsNone() && !AllUnits.ContainsByPredicate([&](const auto& Unit)
		{ return Unit.IsValid() && Unit->Team == Team && Unit->CallSign == Order.TargetSoldier
			&& Unit->IsAlive() && !Recipients.Contains(Unit.Get()); }))
	{
		return TEXT("El soldado a atender no está disponible.");
	}
	if (Order.Action == EYellAction::Retreat && Order.Zone == EYellZone::None)
	{
		Order.Zone = EYellZone::Home;
	}
	if (Order.Zone != EYellZone::None)
	{
		FNavLocation Projected;
		const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
		if (!Nav || !Nav->ProjectPointToNavigation(Position(Order.Zone, Team), Projected, FVector(240, 240, 230)))
		{
			return TEXT("El destino no está disponible en la malla de navegación.");
		}
	}
	bAccepted = true;
	OnOrder.Broadcast(Order, Recipients);
	UE_LOG(LogYellBattle, Display, TEXT("Orden %s equipo=%u peloton=%s accion=%s lugar=%s receptores=%d"),
		*Context.Id.ToString(), Team, *Order.Squad.ToString(), *YellOrder::ActionText(Order.Action),
		*YellOrder::ZoneText(Order.Zone), Recipients.Num());
	const FString Addressee = Order.Soldier.IsNone() ? Order.Squad.ToString() : Recipients[0]->GivenName;
	return FString::Printf(TEXT("¡Copiado, %s! %s %s."), *Addressee, *YellOrder::ActionText(Order.Action),
		*YellOrder::ZoneText(Order.Zone)).Replace(TEXT(" ."), TEXT("."));
}

void AYellBattle::ApplyOrder(const FYellOrder& Order, const TArray<AYellSoldier*>& Recipients)
{
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Recipients.Num(); ++Index)
	{
		AYellSoldier* Soldier = Recipients[Index];
		if (Order.Intent == EYellIntent::Morale)
		{
			Soldier->BoostUntil = Now + MoraleDuration;
			continue;
		}
		const FVector Goal = Order.Zone == EYellZone::None ? Soldier->GetActorLocation()
			: Position(Order.Zone, Soldier->Team) + FormationOffset(Index, Soldier->Team);
		Soldier->Accept(Order, Goal, Goal + FVector(Soldier->Team == 0 ? 470 : -470, 180, 0));
	}
}

float AYellBattle::NextReinforcement(const uint8 Team) const
{
	return Reinforcements[Team].Remaining(GetWorld()->GetTimeSeconds());
}

float AYellBattle::NextMorale() const
{
	return FMath::Max(0.0, MoraleReady - GetWorld()->GetTimeSeconds());
}

FString AYellBattle::TryReinforce(const uint8 Team, const bool bMedical, const FVector* Requester)
{
	if (WinningTeam != INDEX_NONE || (Team == 0 && (!Requester || !IsTerminalNearby(Team, *Requester))))
	{
		return TEXT("Acérquese a la terminal aliada para solicitar refuerzos.");
	}
	const int32 Active = Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; });
	const bool bActiveMedic = Squads.ContainsByPredicate([Team](const FYellSquad& S)
		{ return S.Team == Team && S.bMedic && S.Alive() > 0; });
	switch (Reinforcements[Team].Request(GetWorld()->GetTimeSeconds(), ReinforcementCooldown, Active, bActiveMedic, bMedical))
	{
	case FYellReinforcements::EResult::Full: return TEXT("Ya hay cinco pelotones activos.");
	case FYellReinforcements::EResult::MedicAlreadyActive: return TEXT("Ya existe un pelotón médico activo.");
	case FYellReinforcements::EResult::Busy: return TEXT("La terminal ya tiene una solicitud en curso o en espera.");
	default: return TEXT("Refuerzos en camino. Ojalá traigan café.");
	}
}

void AYellBattle::DamageCore(const uint8 Team, const float Damage)
{
	if (WinningTeam != INDEX_NONE)
	{
		return;
	}
	BaseHealth[Team] = FMath::Max(0.0f, BaseHealth[Team] - Damage);
	if (BaseHealth[Team] == 0)
	{
		WinningTeam = 1 - Team;
		if (Cores[Team].IsValid())
		{
			Cores[Team]->SetActorHiddenInGame(true);
			Cores[Team]->SetActorEnableCollision(false);
		}
		for (const auto& Unit : AllUnits)
		{
			if (Unit.IsValid() && Unit->CanAct())
			{
				Unit->Accept(FYellOrder(), Unit->GetActorLocation(), Unit->GetActorLocation());
			}
		}
		UE_LOG(LogYellBattle, Display, TEXT("Partida finalizada. Equipo vencedor: %d"), WinningTeam);
	}
}

bool AYellBattle::Visible(const AYellSoldier& Observer, const AActor& Target, const FVector& Point, const bool bCone) const
{
	const FVector Delta = Point - Observer.Eye();
	if (Delta.SizeSquared() > FMath::Square(PulseReach)
		|| (bCone && FVector::DotProduct(Delta.GetSafeNormal2D(), Observer.GetActorForwardVector()) < 0.15
			&& Delta.SizeSquared2D() > FMath::Square(300.0)))
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(YellVision), false, &Observer);
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, Observer.Eye(), Point, ECC_Visibility, Params)
		|| Hit.GetActor() == &Target;
}

AYellSoldier* AYellBattle::FindOpponent(AYellSoldier& Soldier) const
{
	AYellSoldier* Result = nullptr;
	double Best = FMath::Square(PulseReach);
	for (const auto& Other : AllUnits)
	{
		if (!Other.IsValid() || Other->Team == Soldier.Team || !Other->CanAct())
		{
			continue;
		}
		const double Distance = FVector::DistSquared(Other->Eye(), Soldier.Eye());
		if (Distance < Best && Visible(Soldier, *Other, Other->Eye()))
		{
			Best = Distance;
			Result = Other.Get();
		}
	}
	return Result;
}

AYellSoldier* AYellBattle::FindPatient(const AYellSoldier& Medic) const
{
	AYellSoldier* Best = nullptr;
	double BestScore = -1e9;
	for (const auto& Unit : AllUnits)
	{
		if (!Unit.IsValid() || Unit.Get() == &Medic || Unit->Team != Medic.Team || !Unit->IsAlive()
			|| (!Medic.CurrentOrder.Target.IsNone() && Medic.CurrentOrder.Target != Unit->Squad)
			|| (!Medic.CurrentOrder.TargetSoldier.IsNone() && Medic.CurrentOrder.TargetSoldier != Unit->CallSign)
			|| Unit->Health >= 97 || (Medic.CurrentOrder.Action == EYellAction::Revive && Unit->CanAct()))
		{
			continue;
		}
		const double Distance = FVector::Dist2D(Medic.GetActorLocation(), Unit->GetActorLocation());
		const double ToZone = FVector::Dist2D(Medic.Destination, Unit->GetActorLocation());
		const bool bRouted = Medic.CurrentOrder.Zone != EYellZone::None;
		if ((bRouted && ToZone > 900)
			|| (!bRouted && Medic.CurrentOrder.Target.IsNone() && Medic.CurrentOrder.TargetSoldier.IsNone() && Distance > 950))
		{
			continue;
		}
		const double Score = (!Unit->CanAct() ? 1500 : 100 - Unit->Health) - Distance * 0.18;
		if (Score > BestScore)
		{
			Best = Unit.Get();
			BestScore = Score;
		}
	}
	return Best;
}

bool AYellBattle::FindCover(const AYellSoldier& Soldier, const AActor& Threat, FVector& Goal) const
{
	double Best = FMath::Square(480.0);
	bool bFound = false;
	for (const FVector& Candidate : CoverPositions)
	{
		const double Distance = FVector::DistSquared2D(Soldier.GetActorLocation(), Candidate);
		if (Distance < Best && GetWorld()->LineTraceTestByChannel(Threat.GetActorLocation() + FVector(0, 0, 20),
			Candidate + FVector(0, 0, 90), ECC_Visibility, FCollisionQueryParams(SCENE_QUERY_STAT(YellCover), false, &Threat)))
		{
			Goal = Candidate;
			Best = Distance;
			bFound = true;
		}
	}
	return bFound;
}

void AYellBattle::SimulatePulse(AYellSoldier& Soldier, AActor* Target, const FVector& Point)
{
	const uint8 Team = Soldier.Team;
	const double Now = GetWorld()->GetTimeSeconds();
	FVector Impact = Point;
	AActor* RivalCore = Cores[1 - Team].Get();
	if (Soldier.CurrentOrder.Action == EYellAction::Attack && Soldier.CurrentOrder.Zone == EYellZone::Rival
		&& RivalCore && Visible(Soldier, *RivalCore, CorePosition(1 - Team), false))
	{
		Impact = CorePosition(1 - Team);
		DamageCore(1 - Team, 14);
	}
	else if (AYellSoldier* Other = Cast<AYellSoldier>(Target))
	{
		Other->Hurt(16, Now);
	}
	else if (AYellCommander* Commander = Cast<AYellCommander>(Target))
	{
		Commander->Hurt(13);
	}
	else
	{
		return;
	}
	DrawDebugLine(GetWorld(), Soldier.Eye(), Impact, Team == 0 ? FColor::Cyan : FColor(255, 105, 46), false, .12f, 0, 2);
	if (Team == 0)
	{
		for (const auto& Observer : AllUnits)
		{
			if (Observer.IsValid() && Observer->Team == 1 && Observer->CanAct()
				&& Observer->CurrentOrder.Action != EYellAction::Scout
				&& FVector::DistSquared2D(Soldier.GetActorLocation(), Observer->GetActorLocation()) < FMath::Square(HearingReach))
			{
				ReportContact({ NAME_None, LaneOf(Soldier.GetActorLocation()), Now, 0.38f });
				break;
			}
		}
	}
}

bool AYellBattle::DetectedByPlayer(const AYellSoldier& Soldier) const
{
	const double* Detected = PlayerIntel.Find(const_cast<AYellSoldier*>(&Soldier));
	return Detected && GetWorld()->GetTimeSeconds() - *Detected < 1.0;
}

FString AYellBattle::RivalPersonality() const
{
	const TCHAR* Names[] = { TEXT("Impulsivo"), TEXT("Calculador"), TEXT("Engañoso") };
	return Names[Personality];
}

void AYellBattle::ReportContact(const FContact& Contact)
{
	const FName Key = Contact.Squad.IsNone() ? FName(*YellOrder::ZoneText(Contact.Lane)) : Contact.Squad;
	Intelligence.Add(Key, Contact);
}

void AYellBattle::UpdateBattle()
{
	if (WinningTeam != INDEX_NONE)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (auto It = SeenRequests.CreateIterator(); It; ++It)
	{
		if (Now - It.Value() > RequestLifetime)
		{
			It.RemoveCurrent();
		}
	}
	AllUnits.RemoveAll([](const auto& Unit) { return !Unit.IsValid(); });
	Squads.RemoveAll([](const FYellSquad& Squad) { return !Squad.Alive(); });
	for (auto It = PlayerIntel.CreateIterator(); It; ++It)
	{
		if (!It.Key().IsValid() || Now - It.Value() > 1.0)
		{
			It.RemoveCurrent();
		}
	}
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		bool bMedical = false;
		if (Reinforcements[Team].Collect(Now, bMedical))
		{
			const TArray<FName> Names = Team == 0 ? TArray<FName>{TEXT("Delta"), TEXT("Eco"), TEXT("Alfa"), TEXT("Bravo")}
				: TArray<FName>{TEXT("Tuerca"), TEXT("Fósforo"), TEXT("Óxido"), TEXT("Chispa"), TEXT("Resorte")};
			for (const FName Name : Names)
			{
				if (SpawnSquad(Team, bMedical ? FName(Team == 0 ? TEXT("Médico") : TEXT("Parche")) : Name, bMedical, 3))
				{
					break;
				}
			}
		}
	}
	for (const auto& WeakUnit : AllUnits)
	{
		if (WinningTeam != INDEX_NONE)
		{
			break;
		}
		AYellSoldier* Unit = WeakUnit.Get();
		if (!Unit)
		{
			continue;
		}
		Unit->Step(*this, Now);
		AYellSoldier* Opponent = Unit->LastSeenOpponent();
		if (Unit->CanAct() && Opponent && Opponent->CanAct())
		{
			if (Unit->Team == 0)
			{
				PlayerIntel.Add(Opponent, Now);
			}
			else
			{
				const FContact Contact = { Opponent->Squad, LaneOf(Opponent->GetActorLocation()), Now, 0.95f };
				if (Unit->CurrentOrder.Action == EYellAction::Scout)
				{
					if (!PendingReports.Contains(Unit))
					{
						PendingReports.Add(Unit, { Contact, Now + 3.0 });
					}
				}
				else
				{
					ReportContact(Contact);
				}
			}
		}
	}
	for (auto It = PendingReports.CreateIterator(); It; ++It)
	{
		if (!It.Key().IsValid() || !It.Key()->CanAct())
		{
			It.RemoveCurrent();
		}
		else if (Now >= It.Value().SendAt)
		{
			ReportContact(It.Value().Contact);
			It.RemoveCurrent();
		}
	}
	if (Now >= NextRivalDecision && WinningTeam == INDEX_NONE)
	{
		RunRival(Now);
		NextRivalDecision = Now + 17.0;
	}
}

void AYellBattle::RunRival(const double Now)
{
	float Pressure[3] = {0, 0, 0};
	for (auto It = Intelligence.CreateIterator(); It; ++It)
	{
		if (Now - It.Value().Reported > IntelLifetime)
		{
			It.RemoveCurrent();
		}
	}
	for (const auto& Entry : Intelligence)
	{
		const FContact& Contact = Entry.Value;
		Pressure[static_cast<int32>(Contact.Lane) - static_cast<int32>(EYellZone::Left)] +=
			Contact.Confidence * (1.0f - (Now - Contact.Reported) / IntelLifetime);
	}
	int32 Strong = 1, Weak = 1;
	for (int32 Lane = 0; Lane < 3; ++Lane)
	{
		if (Pressure[Lane] > Pressure[Strong])
		{
			Strong = Lane;
		}
		if (Pressure[Lane] < Pressure[Weak])
		{
			Weak = Lane;
		}
	}
	TArray<FName> Fighters;
	for (const FYellSquad& Squad : Squads)
	{
		if (Squad.Team == 1 && !Squad.bMedic && Squad.Ready() > 0)
		{
			Fighters.Add(Squad.Id);
		}
	}
	if (Fighters.Num() < 3)
	{
		TryReinforce(1, false);
	}
	if (!Intelligence.IsEmpty())
	{
		Tactic = Personality == 0 ? (Pressure[1] < 0.5f ? 0 : 2)
			: Personality == 1 ? (Pressure[Strong] > 0.64f ? 1 : 4)
			: (Pressure[Strong] > 0.65f ? 3 : 1);
	}
	const EYellZone Lanes[] = { EYellZone::Left, EYellZone::Center, EYellZone::Right };
	for (int32 Index = 0; Index < Fighters.Num(); ++Index)
	{
		FYellOrder Order;
		Order.Squad = Fighters[Index];
		switch (Tactic)
		{
		case 0: Order.Action = Index < 3 ? EYellAction::Attack : EYellAction::Defend;
			Order.Zone = Index < 3 ? EYellZone::Center : EYellZone::Home; break;
		case 1: Order.Action = Index == 0 ? EYellAction::Scout : EYellAction::Attack;
			Order.Zone = Index == 0 ? EYellZone::Center : Lanes[Index % 2 == 0 ? 0 : 2]; break;
		case 2: Order.Action = EYellAction::Attack; Order.Zone = Lanes[Weak]; break;
		case 3:
			Order.Action = Index == 0 ? EYellAction::Retreat : Pressure[1] > 0.65f ? EYellAction::Attack : EYellAction::Scout;
			Order.Zone = Index == 0 ? EYellZone::Home : Pressure[1] > 0.65f ? EYellZone::Center : Lanes[Index % 2 == 0 ? 0 : 2];
			break;
		default: Order.Action = Index == 0 ? EYellAction::Scout : EYellAction::Defend;
			Order.Zone = Index == 0 ? Lanes[Strong] : Lanes[Index % 3]; break;
		}
		if (Now > 36 && Index == 0 && Pressure[Strong] < 0.55f)
		{
			Order.Action = EYellAction::Attack;
			Order.Zone = EYellZone::Rival;
		}
		bool bAccepted = false;
		Dispatch(Order, { FGuid::NewGuid(), EYellChannel::Rival, FVector::ZeroVector, Now }, bAccepted);
	}
}
