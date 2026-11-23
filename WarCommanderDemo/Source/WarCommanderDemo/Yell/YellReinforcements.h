#pragma once

#include "CoreMinimal.h"

struct FYellReinforcements
{
	static constexpr int32 MaxSquads = 5;
	static constexpr int32 MaxMembers = 5;

	enum class EResult : uint8 { Queued, Busy, Full, MedicAlreadyActive };

	EResult Request(double Now, double Cooldown, int32 Active, bool bActiveMedic, bool bRequestMedic)
	{
		if (Active >= MaxSquads)
		{
			return EResult::Full;
		}
		if (bRequestMedic && bActiveMedic)
		{
			return EResult::MedicAlreadyActive;
		}
		if (Arrival > 0 || Now < ReadyAt)
		{
			return EResult::Busy;
		}
		Arrival = Now + 3;
		ReadyAt = Now + Cooldown;
		bMedical = bRequestMedic;
		return EResult::Queued;
	}

	bool Collect(double Now, bool& OutMedical)
	{
		if (Arrival <= 0 || Now < Arrival)
		{
			return false;
		}
		OutMedical = bMedical;
		Arrival = 0;
		return true;
	}

	float Remaining(double Now) const { return FMath::Max(0.0, ReadyAt - Now); }

private:
	double ReadyAt = 0.0;
	double Arrival = 0.0;
	bool bMedical = false;
};
