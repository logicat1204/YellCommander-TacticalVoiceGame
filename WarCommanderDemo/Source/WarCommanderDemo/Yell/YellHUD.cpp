#include "YellPlayer.h"

#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Texture2D.h"
#include "GlobalRenderResources.h"
#include "YellBattle.h"

namespace
{
	const FLinearColor Ink(.012f, .022f, .021f, .78f);
	const FLinearColor Panel(.019f, .034f, .030f, .58f);
	const FLinearColor Paper(.92f, .94f, .86f);
	const FLinearColor Muted(.70f, .77f, .71f);
	const FLinearColor Cyan(.29f, .86f, .91f);
	const FLinearColor Gold(1.f, .64f, .23f);
	const FLinearColor Danger(1.f, .31f, .22f);

	UTexture2D* Sprite(const TCHAR* Name)
	{
		return LoadObject<UTexture2D>(nullptr, *FString::Printf(TEXT("/Game/Yell/Gameplay/HUD/%s.%s"), Name, Name));
	}
}

void AYellHUD::DrawBinocularView(const float Opacity)
{
	const double Width = Canvas->ClipX, Height = Canvas->ClipY;
	const FVector2D Center(Width * .5, Height * .5);
	const double Radius = FMath::Min(Height * .375, Width * .27);
	const double Separation = Radius * .61;
	const double Join = FMath::Sqrt(FMath::Square(Radius) - FMath::Square(Separation));
	const double Left = Center.X - Separation, Right = Center.X + Separation;
	const FLinearColor Mask(.006f, .012f, .014f, Opacity);
	const FLinearColor Glass(.075f, .20f, .18f, .09f * Opacity);
	const FLinearColor Rim(.18f, .26f, .23f, .78f * Opacity);
	DrawRect(Mask, 0, 0, Width, Center.Y - Radius);
	DrawRect(Mask, 0, Center.Y + Radius, Width, Height - Center.Y - Radius);

	TArray<FCanvasUVTri> Mesh;
	Mesh.Reserve(72 * 10);
	auto Quad = [&Mesh](double Y0, double Y1, double Left0, double Right0,
		double Left1, double Right1, const FLinearColor& Tint)
	{
		const FVector2D A(Left0, Y0), B(Right0, Y0), C(Right1, Y1), D(Left1, Y1);
		auto Triangle = [&Mesh, &Tint](const FVector2D& P0, const FVector2D& P1, const FVector2D& P2)
		{
			auto& Tri = Mesh.AddDefaulted_GetRef();
			Tri.V0_Pos = P0; Tri.V1_Pos = P1; Tri.V2_Pos = P2;
			Tri.V0_UV = Tri.V1_UV = Tri.V2_UV = FVector2D::ZeroVector;
			Tri.V0_Color = Tri.V1_Color = Tri.V2_Color = Tint;
		};
		Triangle(A, B, C);
		Triangle(A, C, D);
	};
	auto HalfChord = [Radius](double Y)
	{
		return FMath::Sqrt(FMath::Max(0., FMath::Square(Radius) - FMath::Square(Y)));
	};
	const double Bands[] = {-Radius, -Join, Join, Radius};
	for (int32 Band = 0; Band < 3; ++Band)
	{
		const double Angle0 = FMath::Asin(Bands[Band] / Radius), Angle1 = FMath::Asin(Bands[Band + 1] / Radius);
		for (int32 Row = 0; Row < 24; ++Row)
		{
			const double A = Radius * FMath::Sin(FMath::Lerp(Angle0, Angle1, Row / 24.));
			const double B = Radius * FMath::Sin(FMath::Lerp(Angle0, Angle1, (Row + 1) / 24.));
			const double HalfA = HalfChord(A), HalfB = HalfChord(B);
			const double Y0 = Center.Y + A, Y1 = Center.Y + B;
			Quad(Y0, Y1, 0, Left - HalfA, 0, Left - HalfB, Mask);
			Quad(Y0, Y1, Right + HalfA, Width, Right + HalfB, Width, Mask);
			if (Band == 1)
			{
				Quad(Y0, Y1, Left - HalfA, Right + HalfA, Left - HalfB, Right + HalfB, Glass);
			}
			else
			{
				Quad(Y0, Y1, Left + HalfA, Right - HalfA, Left + HalfB, Right - HalfB, Mask);
				Quad(Y0, Y1, Left - HalfA, Left + HalfA, Left - HalfB, Left + HalfB, Glass);
				Quad(Y0, Y1, Right - HalfA, Right + HalfA, Right - HalfB, Right + HalfB, Glass);
			}
		}
	}
	FCanvasTriangleItem Lenses(Mesh, GWhiteTexture);
	Lenses.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Lenses);

	for (int32 Step = 0; Step < 96; ++Step)
	{
		const double A = 2. * UE_PI * Step / 96., B = 2. * UE_PI * (Step + 1) / 96.;
		for (const double Side : {-1., 1.})
		{
			const double X = Center.X + Separation * Side;
			if (FMath::Cos((A + B) * .5) * Side < -Separation / Radius) continue;
			DrawLine(X + Radius * FMath::Cos(A), Center.Y + Radius * FMath::Sin(A),
				X + Radius * FMath::Cos(B), Center.Y + Radius * FMath::Sin(B), Rim, 2.f);
		}
	}
	DrawLine(Center.X - 11, Center.Y, Center.X - 3, Center.Y, Rim);
	DrawLine(Center.X + 3, Center.Y, Center.X + 11, Center.Y, Rim);
	DrawLine(Center.X, Center.Y - 9, Center.X, Center.Y - 3, Rim);
	DrawLine(Center.X, Center.Y + 3, Center.X, Center.Y + 9, Rim);
}

void AYellHUD::DrawHUD()
{
	Super::DrawHUD();
	const AYellPlayer* Player = Cast<AYellPlayer>(PlayerOwner);
	const AYellBattle* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	const AYellCommander* Commander = Player ? Player->GetPawn<AYellCommander>() : nullptr;
	if (!Canvas || Canvas->ClipX <= 0 || Canvas->ClipY <= 0 || !Player || !Battle || !Commander
		|| Battle->IsMenuScene() || Player->HasMenu() || Battle->Winner() != INDEX_NONE)
	{
		return;
	}
	const float Optics = Commander->OpticBlend();
	if (Optics >= .99f)
	{
		DrawBinocularView(Optics);
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
		FCanvasTextItem Item(FVector2D(X * Scale, Y * Scale), FText::FromString(Text), GEngine->GetSmallFont(), Color);
		Item.Scale = FVector2D(Size * Scale, Size * Scale);
		Item.EnableShadow(FLinearColor(0.f, 0.f, 0.f, .88f), FVector2D(1.f, 1.f));
		Canvas->DrawItem(Item);
	};
	auto Gradient = [this, Scale](float X, float Y, float Width, float Height, FLinearColor Near, float FarAlpha)
	{
		FLinearColor Far = Near;
		Far.A = FarAlpha;
		const FVector2D A(X * Scale, Y * Scale), B((X + Width) * Scale, Y * Scale);
		const FVector2D C((X + Width) * Scale, (Y + Height) * Scale), D(X * Scale, (Y + Height) * Scale);
		TArray<FCanvasUVTri> Triangles;
		auto Triangle = [&Triangles](const FVector2D& P, const FVector2D& Q, const FVector2D& R,
			const FLinearColor& C0, const FLinearColor& C1, const FLinearColor& C2)
		{
			auto& Tri = Triangles.AddDefaulted_GetRef();
			Tri.V0_Pos = P; Tri.V1_Pos = Q; Tri.V2_Pos = R;
			Tri.V0_Color = C0; Tri.V1_Color = C1; Tri.V2_Color = C2;
			Tri.V0_UV = Tri.V1_UV = Tri.V2_UV = FVector2D::ZeroVector;
		};
		Triangle(A, B, C, Near, Far, Far);
		Triangle(A, C, D, Near, Far, Near);
		FCanvasTriangleItem Fade(Triangles, GWhiteTexture);
		Fade.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Fade);
	};
	auto Bar = [&Box](float X, float Y, float Width, float Ratio, const FLinearColor& Color, float Height = 5.f)
	{
		constexpr int32 Segments = 12;
		const float Step = Width / Segments;
		for (int32 Index = 0; Index < Segments; ++Index)
		{
			const float Fill = FMath::Clamp(Ratio * Segments - Index, 0.f, 1.f);
			Box(Panel, X + Index * Step, Y, Step - 1.f, Height);
			if (Fill > 0.f) Box(Color, X + Index * Step, Y, (Step - 1.f) * Fill, Height);
		}
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
		if (X < 90 || X > W - 90 || Y < 34 || Y > H - 136) continue;
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
				Gradient(Left, LabelY - 2, Width + 14, Height + 4, FLinearColor(.013f, .030f, .028f, .64f), .24f);
				Box(Unit->CanAct() ? Cyan : Gold, Left, LabelY - 2, 1.5f, Height + 4);
				Label(Name, Unit->CanAct() ? Paper : Gold, X - Width/2, LabelY, .9f);
				break;
			}
			LabelY -= Height + 5;
		}
	}
	auto Icon = [this, &Box, Scale](UTexture2D* Texture, float X, float Y, float Size, const FLinearColor& Fallback, float Opacity = 1.f)
	{
		if (Texture)
			DrawTexture(Texture, X*Scale, Y*Scale, Size*Scale, Size*Scale, 0, 0, 1, 1,
				FLinearColor(1.f, 1.f, 1.f, Opacity), BLEND_Translucent);
		else
			Box(Fallback, X, Y, Size, Size);
	};
	auto Texture = [this](const TCHAR* Name) -> UTexture2D*
	{
		const FName Key(Name);
		if (const auto* Cached = HUDTextures.Find(Key)) return Cached->Get();
		return HUDTextures.Add(Key, Sprite(Name)).Get();
	};
	const float X = 24, Y = H - 112;
	const float Health = Commander->Health();
	const FLinearColor HealthColor = Health <= 30 ? Danger : Cyan;
	Gradient(X - 11, Y - 12, 322, 103, FLinearColor(.012f, .024f, .020f, .66f), 0.f);
	Label(TEXT("SALUD"), Paper, X, Y, .87f);
	Label(FString::Printf(TEXT("%03.0f"), Health), HealthColor, X + 147, Y - 5, 1.63f);
	Bar(X, Y + 20, 182, Health / 100.f, HealthColor, 6);
	Icon(Texture(Player->bRadio ? TEXT("T_Comm_Glifo_Walkie") : TEXT("T_Comm_Glifo_Habla")), X, Y + 33, 17, Gold);
	Label(Player->bRadio ? TEXT("RADIO") : TEXT("PROXIMIDAD"), Gold, X + 22, Y + 35, .95f);
	if (Player->bRecording)
	{
		Box(Player->bMicReady ? Danger : Gold, X + 127, Y + 39, 5, 5);
		Label(Player->bMicReady ? TEXT("Suelta V para enviar") : TEXT("Abriendo micrófono"), Paper, X + 138, Y + 35, .92f);
	}
	auto Key = [&Box, &Label](const TCHAR* Glyph, const TCHAR* Description, float KeyX, float KeyY, bool bHighlight = false)
	{
		Box(Panel, KeyX, KeyY, 19, 19);
		Box(bHighlight ? Gold : FLinearColor(.46f, .55f, .47f, .69f), KeyX, KeyY + 17, 19, 1);
		Label(Glyph, bHighlight ? Gold : Paper, KeyX + 5, KeyY + 2, .98f);
		Label(Description, Muted, KeyX + 24, KeyY + 2, .90f);
	};
	Key(TEXT("V"), TEXT("Hablar"), X, Y + 62, Player->bRecording);
	Key(TEXT("R"), TEXT("Canal"), X + 71, Y + 62, Player->bRadio);
	Key(TEXT("T"), TEXT("Texto"), X + 136, Y + 62);
	const float MouseX = X + 203, MouseY = Y + 63;
	auto MouseEdge = [&](float AX, float AY, float BX, float BY)
	{
		DrawLine((MouseX + AX) * Scale, (MouseY + AY) * Scale, (MouseX + BX) * Scale,
			(MouseY + BY) * Scale, Muted, 1.f);
	};
	Box(Panel, MouseX + 1, MouseY + 1, 12, 16);
	Box(Gold, MouseX + 7, MouseY + 2, 5, 5);
	MouseEdge(3, 0, 11, 0); MouseEdge(11, 0, 14, 3); MouseEdge(14, 3, 14, 13);
	MouseEdge(14, 13, 11, 16); MouseEdge(11, 16, 3, 16); MouseEdge(3, 16, 0, 13);
	MouseEdge(0, 13, 0, 3); MouseEdge(0, 3, 3, 0); MouseEdge(0, 8, 14, 8);
	Label(TEXT("Binoculares"), Muted, X + 224, Y + 64, .90f);

	int32 SquadCount = 0;
	for (const FYellSquad& Squad : Battle->Roster())
		if (Squad.Team == 0 && Squad.Alive()) ++SquadCount;
	const bool bMedical = Battle->Roster().ContainsByPredicate([](const FYellSquad& Squad)
		{ return Squad.Team == 0 && Squad.bMedic && Squad.Alive() > 0; });
	Gradient(X - 10, 19, 234, 36 + SquadCount * 19 + (bMedical ? 36 : 0), FLinearColor(.012f, .024f, .020f, .66f), 0.f);
	Label(TEXT("PELOTONES ALIADOS"), Paper, X, 26, .94f);
	Box(Gold, X, 46, 35, 1.4f);
	int32 Row = 0;
	for (const FYellSquad& Squad : Battle->Roster())
	{
		if (Squad.Team != 0 || !Squad.Alive()) continue;
		const float RowY = 54 + Row++ * 19;
		Box(Squad.bMedic ? Gold : Cyan, X, RowY + 5, 2, 8);
		Label(Squad.Id.ToString(), Paper, X + 9, RowY, .94f);
		Label(FString::Printf(TEXT("%d / %d"), Squad.Ready(), Squad.Alive()), Muted, X + 130, RowY, .94f);
	}
	if (bMedical)
	{
		const FYellMedicalStatus Supply = Battle->MedicalStatus(0);
		const float RowY = 59 + Row * 19;
		Label(FString::Printf(TEXT("MÉDICOS  %.0f PS  ·  %d REAN."), Supply.Healing, Supply.Revives), Gold, X, RowY, .84f);
		if (Supply.Healing < 200.f || Supply.Revives == 0)
		{
			const int32 Seconds = FMath::CeilToInt(Supply.UntilReset);
			Label(FString::Printf(TEXT("Recarga  %d:%02d"), Seconds / 60, Seconds % 60), Muted, X, RowY + 15, .82f);
		}
	}

	const float MapSize = 200, MapX = W - MapSize - 24, MapY = 24;
	Icon(Texture(TEXT("T_MM_Fondo_Circular")), MapX, MapY, MapSize, Ink, .85f);
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
		const FLinearColor Walkable(.23f, .43f, .37f, .48f);
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
	for (const FBox2D& Road : Battle->ArenaRoads())
	{
		const FVector2D TopLeft = MapPoint(FVector(Road.Max.X, Road.Min.Y, 0));
		const FVector2D BottomRight = MapPoint(FVector(Road.Min.X, Road.Max.Y, 0));
		const FVector2D Size = BottomRight - TopLeft;
		Box(FLinearColor(.45f, .63f, .49f, .65f), TopLeft.X, TopLeft.Y, Size.X, Size.Y);
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
	if (auto* Border = Texture(TEXT("T_MM_Marco_Circular"))) Icon(Border, MapX, MapY, MapSize, Ink, .40f);
	Gradient(MapX - 8, MapY + MapSize + 6, MapSize + 12, 58, FLinearColor(.012f, .024f, .020f, .68f), .10f);
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		const float BaseY = MapY + MapSize + 12 + Team * 27;
		const float Integrity = Battle->CoreHealth(Team) / 500.f;
		Label(Team == 0 ? TEXT("BASE ALIADA") : TEXT("BASE RIVAL"), Paper, MapX, BaseY, .86f);
		Label(FString::Printf(TEXT("%.0f %%"), Integrity * 100.f), Paper, MapX + 157, BaseY, .86f);
		Bar(MapX, BaseY + 15, MapSize - 8, Integrity, Team == 0 ? Cyan : Danger);
	}
	if (Battle->IsTerminalNearby(0,Commander->GetActorLocation()))
	{
		Key(TEXT("E"), TEXT("Refuerzos"), X, Y - 39);
		Key(TEXT("F"), TEXT("Médicos"), X + 94, Y - 39);
	}
	if (Commander->Health() == 0)
	{
		Label(TEXT("Reaparición en la base…"), Danger, W * .5f - 108, H * .5f - 12, 1.35f);
	}
	if (Optics > 0.f) DrawBinocularView(Optics);
}
