#pragma once

#include "CoreMinimal.h"

class FJsonObject;

enum class EYellIntent : uint8 { Order, Morale, Chat, Unknown };
enum class EYellAction : uint8
{
	None, Advance, Defend, Attack, Retreat, Regroup, Patrol, Scout, Hold, Cancel, Heal, Revive
};
enum class EYellZone : uint8 { None, Left, Center, Right, Home, Rival };
enum class EYellChannel : uint8 { Nearby, Radio, Rival };

struct FYellOrder
{
	EYellIntent Intent = EYellIntent::Order;
	EYellAction Action = EYellAction::None;
	EYellZone Zone = EYellZone::None;
	FName Squad;
	FName Target;
	FName Soldier;
	FName TargetSoldier;
};

struct FYellRequestContext
{
	FGuid Id;
	EYellChannel Channel = EYellChannel::Radio;
	FVector Origin = FVector::ZeroVector;
	double Started = 0;
	double ReleasedAt = 0;
};

namespace YellOrder
{
	bool Parse(const FJsonObject& Json, FYellOrder& Order, FString& Reason, double MinConfidence = 0.70);
	bool IsMedical(EYellAction Action);
	bool NeedsZone(EYellAction Action);
	FString ActionText(EYellAction Action);
	FString ZoneText(EYellZone Zone);
}
