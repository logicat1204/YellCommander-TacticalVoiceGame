#pragma once

#include "CoreMinimal.h"

struct FYellMedicalStatus
{
	float Healing = 200.f;
	int32 Revives = 1;
	double UntilReset = 300.;
};

// Both medics on a team draw from the same stock for each five-minute period.
class FYellMedicalSupplies
{
public:
	FYellMedicalStatus Status(double Elapsed) const
	{
		const int32 Period = PeriodAt(Elapsed);
		FYellMedicalStatus Result = Period == ActivePeriod ? Stock : FYellMedicalStatus{};
		Result.UntilReset = (Period + 1) * PeriodSeconds - FMath::Max(0., Elapsed);
		return Result;
	}

	float SpendHealing(double Elapsed, float Requested)
	{
		Refresh(Elapsed);
		const float Used = FMath::Clamp(Requested, 0.f, Stock.Healing);
		Stock.Healing -= Used;
		return Used;
	}

	bool SpendRevive(double Elapsed)
	{
		Refresh(Elapsed);
		if (Stock.Revives == 0) return false;
		--Stock.Revives;
		return true;
	}

private:
	static constexpr double PeriodSeconds = 300.;
	static int32 PeriodAt(double Elapsed) { return FMath::FloorToInt(FMath::Max(0., Elapsed) / PeriodSeconds); }

	void Refresh(double Elapsed)
	{
		const int32 Period = PeriodAt(Elapsed);
		if (Period == ActivePeriod) return;
		ActivePeriod = Period;
		Stock = {};
	}

	int32 ActivePeriod = 0;
	FYellMedicalStatus Stock;
};
