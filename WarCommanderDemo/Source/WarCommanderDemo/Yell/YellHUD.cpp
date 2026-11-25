#include "YellPlayer.h"

#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Texture2D.h"
#include "GlobalRenderResources.h"
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

	UTexture2D* Sprite(const TCHAR* Name)
	{
		return LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/Yell/Gameplay/HUD/%s.%s"), Name, Name));
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
	FVector Eye;
	FRotator View;
	Player->GetPlayerViewPoint(Eye, View);
	TArray<FBox2D> Nameplates;
	for (const auto& Unit : Battle->Units())
	{
		if (!Unit.IsValid() || Unit->Team != 0 || !Unit->IsAlive()) continue;
		const FVector Head = Unit->GetActorLocation() + FVector(0, 0, Unit->CanAct() ? 111.f : 1.f);
		if (FVector::DistSquared(Eye, Head) > FMath::Square(3400.f)) continue;
		const FCollisionQueryParams Sight(SCENE_QUERY_STAT(YellNameplate), false, Commander);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Head, ECC_Visibility, Sight) &&
			Hit.GetActor() != Unit.Get()) continue;
		FVector2D Screen;
		if (!Player->ProjectWorldLocationToScreen(Head, Screen, true)) continue;
		const float X = Screen.X / Scale, Y = Screen.Y / Scale;
		if (X < 90 || X > W - 90 || Y < 34 || Y > H - 120) continue;
		const FString Name = Unit->GivenName + TEXT(" · ") + Unit->Squad.ToString();
		float Width, Height;
		GetTextSize(Name, Width, Height, GEngine->GetSmallFont(), .9f);
		const float Left = X - Width/2 - 5;
		float LabelY = Y;
		for (int32 Tier = 0; Tier < 4; ++Tier)
		{
			const FBox2D Bounds(FVector2D(Left, LabelY - 2), FVector2D(Left + Width + 10, LabelY + Height + 2));
			if (!Nameplates.ContainsByPredicate([&Bounds](const FBox2D& Other) { return Bounds.Intersect(Other); }))
			{
				Nameplates.Add(Bounds);
				Box(Ink, Left, LabelY - 2, Width + 10, Height + 4);
				Label(Name, Unit->CanAct() ? Paper : Gold, X - Width/2, LabelY, .9f);
				break;
			}
			LabelY -= Height + 5;
		}
	}
	auto Icon = [this, &Box, Scale](UTexture2D* Texture, float X, float Y, float Size, const FLinearColor& Fallback)
	{
		if (Texture)
			DrawTexture(Texture, X*Scale, Y*Scale, Size*Scale, Size*Scale, 0, 0, 1, 1,
				FLinearColor::White, BLEND_Translucent);
		else
			Box(Fallback, X, Y, Size, Size);
	};
	auto Texture = [this](const TCHAR* Name) -> UTexture2D*
	{
		const FName Key(Name);
		if (const auto* Cached = HUDTextures.Find(Key)) return Cached->Get();
		return HUDTextures.Add(Key, Sprite(Name)).Get();
	};
	const float X = 22, Y = H - 114;
	const float Health = Commander->Health();
	Box(Ink, X, Y, 318, 92);
	Icon(Texture(Health <= 30 ? TEXT("T_Heart_Critico") : Health <= 65 ? TEXT("T_Heart_Herido") :
		TEXT("T_Heart_Sano")), X+11, Y+7, 36, Danger);
	Label(FString::Printf(TEXT("Comandante   %.0f / 100"), Health), Paper, X+56, Y+8, 1.f);
	Bar(X+56, Y+29, 247, Health/100.f, Health <= 30 ? Danger : Cyan);
	Icon(Texture(Player->bRadio ? TEXT("T_Comm_Glifo_Walkie") : TEXT("T_Comm_Glifo_Habla")), X+14, Y+43, 25, Gold);
	Label(Player->bRadio ? TEXT("Walkie-talkie equipado") : TEXT("Voz de proximidad"), Gold, X+56, Y+44, .99f);
	Label(Player->bRecording ? TEXT("Grabando   ·   Suelta V para enviar") : TEXT("V  Hablar     R  Cambiar canal     T  Escribir"), Muted, X+14, Y+70, .9f);

	int32 SquadCount = 0;
	for (const FYellSquad& Squad : Battle->Roster())
		if (Squad.Team == 0 && Squad.Alive()) ++SquadCount;
	Box(Ink, X, 24, 184, 30 + SquadCount * 23);
	Label(TEXT("Pelotones aliados"), Paper, X+11, 30, 1.f);
	int32 Row = 0;
	for (const FYellSquad& Squad : Battle->Roster())
	{
		if (Squad.Team != 0 || !Squad.Alive()) continue;
		const float RowY = 51 + Row++ * 23;
		Label(Squad.Id.ToString(), Squad.bMedic ? Gold : Cyan, X+11, RowY, .94f);
		Label(FString::Printf(TEXT("%d / %d"), Squad.Ready(), Squad.Alive()), Paper, X+130, RowY, .94f);
	}

	const float MapSize = 216, MapX = W - MapSize - 24, MapY = 24;
	Icon(Texture(TEXT("T_MM_Fondo_Circular")), MapX, MapY, MapSize, Ink);
	auto MapPoint = [&](const FVector& Location)
	{
		const FVector2D Extent = Battle->ArenaExtent();
		const FVector2D Offset(FMath::Clamp(Location.Y / Extent.Y,-1.,1.),
			FMath::Clamp(-Location.X / Extent.X,-1.,1.));
		return FVector2D(MapX + MapSize/2, MapY + MapSize/2) + Offset * (MapSize*.31);
	};
	const auto& Terrain = Battle->WalkableTriangles();
	if (!Terrain.IsEmpty())
	{
		TArray<FCanvasUVTri> Triangles;
		Triangles.Reserve(Terrain.Num() / 3);
		const FLinearColor Walkable(.34f,.57f,.49f,.57f);
		for (int32 Index = 0; Index < Terrain.Num(); Index += 3)
		{
			auto& Tri = Triangles.AddDefaulted_GetRef();
			Tri.V0_Pos = MapPoint(Terrain[Index]) * Scale;
			Tri.V1_Pos = MapPoint(Terrain[Index+1]) * Scale;
			Tri.V2_Pos = MapPoint(Terrain[Index+2]) * Scale;
			Tri.V0_Color = Tri.V1_Color = Tri.V2_Color = Walkable;
			Tri.V0_UV = Tri.V1_UV = Tri.V2_UV = FVector2D::ZeroVector;
		}
		FCanvasTriangleItem Overlay(Triangles, GWhiteTexture);
		Overlay.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Overlay);
	}
	auto Marker = [&](UTexture2D* Texture, const FVector& Location, float Size, const FLinearColor& Fallback)
	{
		const FVector2D Point = MapPoint(Location);
		Icon(Texture, Point.X - Size/2, Point.Y - Size/2, Size, Fallback);
	};
	Marker(Texture(TEXT("T_MM_Estructura_BaseAliada")), Battle->CorePosition(0), 19, Paper);
	for (const auto& Unit : Battle->Units())
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->IsAlive())
		{
			const TCHAR* Name = Unit->bMedic ? TEXT("T_MM_Medico")
				: Unit->Squad == TEXT("Bravo") ? TEXT("T_MM_Soldado_Bravo") : TEXT("T_MM_Soldado_Alpha");
			Marker(Texture(Name), Unit->GetActorLocation(), Unit->CanAct() ? 12 : 8, Cyan);
		}
	}
	Marker(Texture(TEXT("T_MM_Jugador")), Commander->GetActorLocation(), 17, Gold);
	if (auto* Border = Texture(TEXT("T_MM_Marco_Circular"))) Icon(Border, MapX, MapY, MapSize, Ink);
	Box(Ink, MapX, MapY+MapSize+7, MapSize, 64);
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		const float BaseY = MapY + MapSize + 12 + Team * 27;
		const float Integrity = Battle->CoreHealth(Team) / 500.f;
		Label(FString::Printf(TEXT("%s    %.0f %%"), Team == 0 ? TEXT("Base aliada") : TEXT("Base rival"),
			Integrity * 100.f), Paper, MapX+11, BaseY, .98f);
		Bar(MapX+11, BaseY+18, MapSize-22, Integrity, Team == 0 ? Cyan : Danger);
	}
	if (Battle->IsTerminalNearby(0,Commander->GetActorLocation()))
		Label(TEXT("E  Refuerzos     F  Médicos"),Paper,X,Y-22,1.f);
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
