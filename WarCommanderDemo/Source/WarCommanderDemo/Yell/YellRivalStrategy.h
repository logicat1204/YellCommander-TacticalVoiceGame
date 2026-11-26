#pragma once

#include "CoreMinimal.h"

enum class EYellDifficulty : uint8 { Easy, Normal, Hard };
enum class EYellRivalMove : uint8 { Withdraw, Guard, Stage, Assault };

struct FYellRivalPolicy
{
	double IntelInterval;
	float Aggression;

	static FYellRivalPolicy For(EYellDifficulty Difficulty)
	{
		switch (Difficulty)
		{
		case EYellDifficulty::Easy: return {7.0, .2f};
		case EYellDifficulty::Hard: return {1.25, .85f};
		default: return {3.5, .5f};
		}
	}

	static EYellDifficulty Parse(const FString& Name)
	{
		if (Name == TEXT("Easy")) return EYellDifficulty::Easy;
		if (Name == TEXT("Hard")) return EYellDifficulty::Hard;
		return EYellDifficulty::Normal;
	}

	static const TCHAR* Name(EYellDifficulty Difficulty)
	{
		switch (Difficulty)
		{
		case EYellDifficulty::Easy: return TEXT("Easy");
		case EYellDifficulty::Hard: return TEXT("Hard");
		default: return TEXT("Normal");
		}
	}

	EYellRivalMove Decide(bool bEmergency, bool bGuard, bool bOvermatched, bool bStaged, bool bHasCover,
		bool bRouteContested, float StrengthRatio, bool bOutnumbers, bool bClear) const
	{
		if (bEmergency) return bGuard ? EYellRivalMove::Guard : EYellRivalMove::Withdraw;
		if (bGuard) return EYellRivalMove::Guard;
		if (bOvermatched) return EYellRivalMove::Withdraw;
		const float Advantage = FMath::Lerp(1.65f, 1.05f, Aggression);
		if (bStaged && bHasCover && !bRouteContested && ((bOutnumbers && StrengthRatio >= Advantage) || bClear))
			return EYellRivalMove::Assault;
		return EYellRivalMove::Stage;
	}
};
