#include "YellPlayer.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "YellBattle.h"

namespace
{
	const FLinearColor Ink(.027f, .063f, .075f, .93f);
	const FLinearColor Panel(.064f, .119f, .133f, .9f);
	const FLinearColor Paper(.86f, .94f, .94f, 1);
	const FLinearColor Muted(.52f, .69f, .71f, 1);
	const FLinearColor Cyan(.27f, .88f, .91f, 1);
	const FLinearColor Gold(.96f, .68f, .30f, 1);
	const FLinearColor Danger(.99f, .35f, .23f, 1);
	const FLinearColor Medic(.40f, .91f, .48f, 1);

	FString Countdown(const float Seconds)
	{
		return Seconds > 0 ? FString::Printf(TEXT("%d s"), FMath::CeilToInt(Seconds)) : TEXT("listo");
	}
}

void AYellHUD::DrawHUD()
{
	Super::DrawHUD();
	const AYellPlayer* Player = Cast<AYellPlayer>(PlayerOwner);
	const AYellBattle* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	const AYellCommander* Commander = Player ? Player->GetPawn<AYellCommander>() : nullptr;
	if (!Canvas || !Player || !Battle || !Commander)
	{
		return;
	}
	const float Scale = FMath::Min(Canvas->ClipX / 1210.0f, Canvas->ClipY / 720.0f);
	const float W = Canvas->ClipX / Scale, H = Canvas->ClipY / Scale;
	auto Box = [this, Scale](const FLinearColor& Color, float X, float Y, float Width, float Height)
	{
		DrawRect(Color, X * Scale, Y * Scale, Width * Scale, Height * Scale);
	};
	auto Label = [this, Scale](const FString& Text, const FLinearColor& Color, float X, float Y, float Size)
	{
		DrawText(Text, Color, X * Scale, Y * Scale, GEngine->GetSmallFont(), Size * Scale);
	};
	auto Bar = [&Box](float X, float Y, float Width, float Ratio, const FLinearColor& Color)
	{
		Box(Panel, X, Y, Width, 5);
		Box(Color, X, Y, Width * FMath::Clamp(Ratio, 0.0f, 1.0f), 5);
	};
	const float X = 22.0f, Y = 22.0f;
	const float MapWidth = 237, MapX = W - MapWidth - X, MapY = Y + 31;
	Box(Ink, X, Y, 295, 135);
	Box(Cyan, X, Y, 295, 3);
	Label(TEXT("YELL COMMANDER"), Paper, X + 13, Y + 11, 1.42f);
	Label(TEXT("VALLE ALFA"), Muted, X + 13, Y + 33, 1.0f);
	Label(FString::Printf(TEXT("COMANDANTE   %03.0f"), Commander->Health()), Paper, X + 13, Y + 56, .95f);
	Bar(X + 13, Y + 73, 269, Commander->Health() / 100, Cyan);
	Label(FString::Printf(TEXT("BASE ALIADA   %03.0f"), Battle->CoreHealth(0)), Paper, X + 13, Y + 89, .95f);
	Label(FString::Printf(TEXT("RIVAL   %03.0f"), Battle->CoreHealth(1)), Muted, X + 191, Y + 89, .95f);
	Bar(X + 13, Y + 110, 129, Battle->CoreHealth(0) / 500, Cyan);
	Bar(X + 153, Y + 110, 129, Battle->CoreHealth(1) / 500, Danger);

	float AllyY = Y + 150;
	const int32 Count = Battle->AlliedNames().Num();
	Box(Ink, X, AllyY, 295, Count * 29 + 53);
	Label(TEXT("PELOTONES ALIADOS"), Muted, X + 13, AllyY + 9, 1.05f);
	AllyY += 31;
	for (const FYellSquad& Squad : Battle->Roster())
	{
		if (Squad.Team != 0)
		{
			continue;
		}
		const FLinearColor Tint = Squad.bMedic ? Medic : Cyan;
		const AYellSoldier* Leader = nullptr;
		bool bInspired = false;
		for (const auto& Member : Squad.Members)
		{
			if (Member.IsValid() && Member->CanAct())
			{
				Leader = Leader ? Leader : Member.Get();
				bInspired |= Member->BoostUntil > GetWorld()->GetTimeSeconds();
			}
		}
		Box(Panel, X + 7, AllyY - 2, 281, 23);
		Box(bInspired ? Gold : Tint, X + 7, AllyY - 2, 3, 23);
		Label(Squad.Id.ToString(), Tint, X + 15, AllyY + 3, 1.04f);
		Label(Leader ? YellOrder::ActionText(Leader->CurrentOrder.Action) : TEXT("incapacitado"),
			Paper, X + 91, AllyY + 4, .89f);
		Label(FString::Printf(TEXT("%d/%d"), Squad.Ready(), Squad.Alive()), Muted, X + 245, AllyY + 4, .89f);
		AllyY += 29;
	}
	Label(FString::Printf(TEXT("Refuerzos %s     Moral %s"), *Countdown(Battle->NextReinforcement(0)),
		*Countdown(Battle->NextMorale())), Muted, X + 13, AllyY + 1, .91f);

	Box(Ink, MapX, Y, MapWidth, 235);
	Box(Gold, MapX, Y, MapWidth, 3);
	Label(TEXT("MAPA TÁCTICO"), Paper, MapX + 11, Y + 11, 1.05f);
	auto Map = [MapX, MapY](const FVector& Point)
	{
		return FVector2D(MapX + 117 + Point.Y / 24.5, MapY + 88 - Point.X / 49.0);
	};
	for (const EYellZone Zone : {EYellZone::Left, EYellZone::Center, EYellZone::Right})
	{
		const FVector2D Position = Map(Battle->Position(Zone, 0));
		Box(Panel, Position.X - 20, MapY + 7, 40, 160);
		const TCHAR* Name = Zone == EYellZone::Left ? TEXT("IZQ") : Zone == EYellZone::Right ? TEXT("DER") : TEXT("CTR");
		Label(Name, Muted, Position.X - 10, MapY + 170, .80f);
	}
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		const FVector2D Point = Map(Battle->CorePosition(Team));
		Box(Team == 0 ? Cyan : Danger, Point.X - 7, Point.Y - 5, 14, 10);
	}
	for (const auto& Unit : Battle->Units())
	{
		if (!Unit.IsValid() || !Unit->IsAlive() || (Unit->Team == 1 && !Battle->DetectedByPlayer(*Unit)))
		{
			continue;
		}
		const FVector2D Point = Map(Unit->GetActorLocation());
		if (Unit->Team == 0 && Player->Model == TEXT("D") &&
			FVector::DistSquared(Commander->GetActorLocation(),Unit->GetActorLocation()) < FMath::Square(1300.0))
		{
			FVector2D Screen;
			if (Player->ProjectWorldLocationToScreen(Unit->Eye()+FVector(0,0,42),Screen,true))
				Label(Unit->GivenName + TEXT(" · ") + Unit->Squad.ToString(),Paper,Screen.X,Screen.Y,.84f);
		}
		const FLinearColor Tint = !Unit->CanAct() ? Gold : Unit->Team == 1 ? Danger : Unit->bMedic ? Medic : Cyan;
		Box(Tint, Point.X - 2, Point.Y - 2, 4, 4);
		if (Unit->Team == 0 && Unit->CanAct() && Unit->CurrentOrder.Zone != EYellZone::None)
		{
			const FVector2D Goal = Map(Unit->Destination);
			Box(FLinearColor(Tint.R, Tint.G, Tint.B, .40f), Goal.X - 2, Goal.Y - 2, 4, 4);
		}
	}
	const FVector2D Point = Map(Commander->GetActorLocation());
	Box(Paper, Point.X - 3, Point.Y - 3, 6, 6);
	Label(FString::Printf(TEXT("Rival · %s"), *Battle->RivalPersonality()), Muted, MapX + 11, MapY + 187, .96f);

	Box(Paper, W * .5f - 5, H * .5f, 10, 1);
	Box(Paper, W * .5f, H * .5f - 5, 1, 10);
	const float RadioWidth = FMath::Min(W - 48.0f, 700.0f);
	const float RadioX = (W - RadioWidth) * .5f, RadioY = H - 108;
	Box(Ink, RadioX, RadioY, RadioWidth, 85);
	Box(Player->bRecording ? Danger : Gold, RadioX, RadioY, RadioWidth, 3);
	const FString Channel = Player->bRadio ? TEXT("RADIO") : TEXT("PROXIMIDAD");
	const FString State = Player->bRecording ? (Player->bMicReady ? TEXT("GRABANDO") : TEXT("PREPARANDO"))
		: Player->PendingRequests() ? TEXT("PROCESANDO") : TEXT("EN ESPERA");
	Label(FString::Printf(TEXT("%s  /  %s  /  MODELO %s"), *Channel, *State, *Player->Model),
		Gold, RadioX + 14, RadioY + 9, 1.05f);
	Label(Player->Status.Left(102), Paper, RadioX + 14, RadioY + 30, 1.03f);
	if (Player->bRecording)
	{
		Box(Panel, RadioX + RadioWidth - 114, RadioY + 13, 98, 4);
		Box(Cyan, RadioX + RadioWidth - 114, RadioY + 13, 98 * Player->MicLevel, 4);
	}
	Label(FString::Printf(TEXT("V Hablar   T Escribir   R Canal   F2 Modelo   F3 Diagnóstico   ·   %d en proceso / %d audios"),
		Player->PendingRequests(), Player->PendingAudio()), Muted, RadioX + 14, RadioY + 58, .94f);
	if (Battle->IsTerminalNearby(0, Commander->GetActorLocation()))
	{
		Label(TEXT("E  Pedir refuerzos    F  Pedir médicos"), Gold, X, H - 59, 1);
	}
	if (Player->bDetails)
	{
		const float DebugWidth = 590, DebugHeight = 266;
		const float DX = (W - DebugWidth) / 2, DY = 50;
		Box(Ink, DX, DY, DebugWidth, DebugHeight);
		Box(Cyan, DX, DY, 3, DebugHeight);
		Label(TEXT("DIAGNÓSTICO NLP"), Cyan, DX + 11, DY + 8, 1.25f);
		Label(Player->StageTiming, Gold, DX + 11, DY + 29, .91f);
		Label(Player->VoiceDiagnostics.Left(102), Muted, DX + 11, DY + 47, .88f);
		Label(TEXT("Texto   ") + Player->Transcript.Left(99), Paper, DX + 11, DY + 67, .88f);
		for (int32 Offset = 0; Offset < Player->DebugJson.Len() && Offset < 380; Offset += 95)
		{
			Label(Player->DebugJson.Mid(Offset, 95), Muted, DX + 11, DY + 87 + Offset / 95 * 14, .86f);
		}
		Label(TEXT("RADIO RECIENTE"), Cyan, DX + 11, DY + 150, .99f);
		for (int32 Index = 0; Index < Player->Recent.Num(); ++Index)
		{
			Label(Player->Recent[Index].Left(99), Paper, DX + 11, DY + 169 + Index * 15, .86f);
		}
	}
	if (Battle->Winner() != INDEX_NONE)
	{
		const float Left = W * .5f - 185, Top = H * .5f - 65;
		const FLinearColor Accent = Battle->Winner() == 0 ? Cyan : Danger;
		Box(Ink, Left, Top, 370, 130);
		Box(Accent, Left, Top, 370, 4);
		Label(Battle->Winner() == 0 ? TEXT("VICTORIA") : TEXT("DERROTA"), Accent, Left + 21, Top + 21, 2.2f);
		Label(TEXT("F5  Volver a desplegar"), Paper, Left + 21, Top + 77, 1.24f);
	}
	else if (Commander->Health() == 0)
	{
		Box(Ink, W * .5f - 145, H * .5f - 31, 290, 62);
		Label(TEXT("Reaparición en la base…"), Danger, W * .5f - 126, H * .5f - 12, 1.35f);
	}
}
