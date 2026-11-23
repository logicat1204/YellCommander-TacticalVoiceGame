#include "YellOrder.h"

#include "Dom/JsonObject.h"

namespace
{
	const TMap<FString, EYellIntent> Intents = {
		{TEXT("orden"), EYellIntent::Order}, {TEXT("motivacion"), EYellIntent::Morale},
		{TEXT("charla"), EYellIntent::Chat}, {TEXT("desconocido"), EYellIntent::Unknown}
	};
	const TMap<FString, EYellAction> Actions = {
		{TEXT("avanzar"), EYellAction::Advance}, {TEXT("defender"), EYellAction::Defend},
		{TEXT("atacar"), EYellAction::Attack}, {TEXT("retirarse"), EYellAction::Retreat},
		{TEXT("reagruparse"), EYellAction::Regroup}, {TEXT("patrullar"), EYellAction::Patrol},
		{TEXT("explorar"), EYellAction::Scout}, {TEXT("mantener_posicion"), EYellAction::Hold},
		{TEXT("cancelar_orden"), EYellAction::Cancel}, {TEXT("curar"), EYellAction::Heal},
		{TEXT("reanimar"), EYellAction::Revive}
	};
	const TMap<FString, EYellZone> Zones = {
		{TEXT("flanco_izquierdo"), EYellZone::Left}, {TEXT("centro"), EYellZone::Center},
		{TEXT("flanco_derecho"), EYellZone::Right}, {TEXT("base_aliada"), EYellZone::Home},
		{TEXT("base_enemiga"), EYellZone::Rival}
	};

	bool ReadUnit(const FJsonObject& Json, const TCHAR* Key, FName& Squad, FName& Soldier)
	{
		const TSharedPtr<FJsonValue> Field = Json.TryGetField(Key);
		if (Field && Field->IsNull())
		{
			return true;
		}
		const TSharedPtr<FJsonObject>* Object = nullptr;
		FString Name, Type;
		if (!Json.TryGetObjectField(Key, Object) || !Object || !Object->IsValid() || (*Object)->Values.Num() != 2
			|| !(*Object)->TryGetStringField(TEXT("type"), Type) || (Type != TEXT("peloton") && Type != TEXT("soldado"))
			|| !(*Object)->TryGetStringField(TEXT("name"), Name)
			|| Name.IsEmpty() || Name.Len() > 64 || Name != Name.TrimStartAndEnd())
		{
			return false;
		}
		FName& Result = Type == TEXT("soldado") ? Soldier : Squad;
		Result = FName(*Name);
		return !Result.IsNone();
	}
}

bool YellOrder::Parse(const FJsonObject& Json, FYellOrder& Order, FString& Reason, const double MinConfidence)
{
	const TSharedPtr<FJsonValue> Version = Json.TryGetField(TEXT("version"));
	FString IntentName;
	FYellOrder Parsed;
	Reason = TEXT("Formato de orden v1 inválido.");
	if (Json.Values.Num() != 7 || !Version || Version->Type != EJson::Number || Version->AsNumber() != 1
		|| !Json.TryGetStringField(TEXT("intent"), IntentName) || !Intents.Contains(IntentName)
		|| !ReadUnit(Json, TEXT("subject"), Parsed.Squad, Parsed.Soldier)
		|| !ReadUnit(Json, TEXT("target"), Parsed.Target, Parsed.TargetSoldier))
	{
		return false;
	}
	Parsed.Intent = Intents[IntentName];
	const TSharedPtr<FJsonValue> Action = Json.TryGetField(TEXT("action"));
	const TSharedPtr<FJsonValue> Location = Json.TryGetField(TEXT("location"));
	const TSharedPtr<FJsonValue> Confidence = Json.TryGetField(TEXT("model_confidence"));
	if (!Action || !Location || !Confidence)
	{
		return false;
	}
	if (!Action->IsNull())
	{
		FString Id;
		if (Action->Type != EJson::String || !Action->TryGetString(Id) || !Actions.Contains(Id))
		{
			return false;
		}
		Parsed.Action = Actions[Id];
	}
	if (!Location->IsNull())
	{
		const TSharedPtr<FJsonObject>* Object = nullptr;
		FString Id;
		if (!Location->TryGetObject(Object) || !Object || !Object->IsValid() || (*Object)->Values.Num() != 1
			|| !(*Object)->TryGetStringField(TEXT("id"), Id) || !Zones.Contains(Id))
		{
			return false;
		}
		Parsed.Zone = Zones[Id];
	}
	if (!Confidence->IsNull())
	{
		double Score = 0.0;
		if (Confidence->Type != EJson::Number || !Confidence->TryGetNumber(Score)
			|| !FMath::IsFinite(Score) || Score < 0 || Score > 1)
		{
			return false;
		}
		if ((Parsed.Intent == EYellIntent::Order || Parsed.Intent == EYellIntent::Morale) && Score < MinConfidence)
		{
			Reason = TEXT("Interferencia en la radio. Repita, mi General.");
			return false;
		}
	}
	if (Parsed.Intent != EYellIntent::Order && (Parsed.Action != EYellAction::None
		|| Parsed.Zone != EYellZone::None || !Parsed.Target.IsNone() || !Parsed.TargetSoldier.IsNone()))
	{
		return false;
	}
	if ((Parsed.Intent == EYellIntent::Unknown || Parsed.Intent == EYellIntent::Chat)
		&& (!Parsed.Squad.IsNone() || !Parsed.Soldier.IsNone()))
	{
		return false;
	}
	if ((!Parsed.Target.IsNone() || !Parsed.TargetSoldier.IsNone()) && !IsMedical(Parsed.Action))
	{
		return false;
	}
	Order = Parsed;
	Reason.Reset();
	return true;
}

bool YellOrder::IsMedical(const EYellAction Action)
{
	return Action == EYellAction::Heal || Action == EYellAction::Revive;
}

bool YellOrder::NeedsZone(const EYellAction Action)
{
	return Action == EYellAction::Advance || Action == EYellAction::Attack || Action == EYellAction::Patrol
		|| Action == EYellAction::Scout || Action == EYellAction::Regroup || Action == EYellAction::Defend;
}

FString YellOrder::ActionText(const EYellAction Action)
{
	for (const auto& Pair : Actions)
	{
		if (Pair.Value == Action)
		{
			return Pair.Key.Replace(TEXT("_"), TEXT(" "));
		}
	}
	return TEXT("en espera");
}

FString YellOrder::ZoneText(const EYellZone Zone)
{
	for (const auto& Pair : Zones)
	{
		if (Pair.Value == Zone)
		{
			return Pair.Key.Replace(TEXT("_"), TEXT(" "));
		}
	}
	return FString();
}
