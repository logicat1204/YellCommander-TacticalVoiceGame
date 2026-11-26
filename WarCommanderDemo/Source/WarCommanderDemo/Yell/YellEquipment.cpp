#include "YellPlayer.h"

#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
	constexpr float OpticFOV = 30.f;

	void ShowModel(USceneComponent& Model, bool bShow)
	{
		if (Model.IsVisible() != bShow) Model.SetVisibility(bShow, true);
	}
}

void AYellCommander::BeginPlay()
{
	Super::BeginPlay();
	BuildEquipmentModels();
	ResetEquipment();
}

void AYellCommander::BuildEquipmentModels()
{
	auto* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	auto* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	auto* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	auto* Surface = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Yell/Art/Materials/Master/M_Equipo.M_Equipo"));
	auto Finish = [this, Surface](const FLinearColor& Color, const float Roughness, const float Glow = 0.f) -> UMaterialInterface*
	{
		if (!Surface) return nullptr;
		auto* Material = UMaterialInstanceDynamic::Create(Surface, this);
		Material->SetVectorParameterValue(TEXT("Color"), Color);
		Material->SetScalarParameterValue(TEXT("Roughness"), Roughness);
		Material->SetScalarParameterValue(TEXT("EmissiveStrength"), Glow);
		return Material;
	};
	auto* Housing = Finish(FLinearColor(.093f, .12f, .070f), .57f);
	auto* Rubber = Finish(FLinearColor(.015f, .022f, .024f), .78f);
	auto* Metal = Finish(FLinearColor(.155f, .192f, .175f), .42f);
	auto* Glass = Finish(FLinearColor(.026f, .18f, .22f), .18f, .16f);
	auto* Screen = Finish(FLinearColor(.052f, .138f, .097f), .44f, .39f);
	auto* Signal = Finish(FLinearColor(.66f, .48f, .096f), .45f, .57f);
	auto* Sleeve = Finish(FLinearColor(.18f, .205f, .102f), .9f);
	auto* Glove = Finish(FLinearColor(.062f, .078f, .054f), .86f);

	auto Part = [this](USceneComponent* Root, UStaticMesh* Shape, UMaterialInterface* Material,
		const FVector& Center, const FVector& Size, const FRotator& Rotation = FRotator::ZeroRotator)
	{
		auto* Component = NewObject<UStaticMeshComponent>(this);
		AddInstanceComponent(Component);
		Component->SetupAttachment(Root);
		Component->SetStaticMesh(Shape);
		Component->SetMaterial(0, Material);
		Component->SetRelativeLocationAndRotation(Center, Rotation);
		Component->SetRelativeScale3D(Size / 100.);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetCanEverAffectNavigation(false);
		Component->SetCastShadow(false);
		Component->SetReceivesDecals(false);
		Component->SetOnlyOwnerSee(true);
		Component->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
		Component->RegisterComponent();
		Component->PrecachePSOs();
	};
	auto Span = [&](USceneComponent* Root, UMaterialInterface* Material, const FVector& From, const FVector& To, float Width)
	{
		Part(Root, Cylinder, Material, (From + To) * .5, FVector(Width, Width, (To - From).Size()),
			FRotationMatrix::MakeFromZ(To - From).Rotator());
	};
	auto Hand = [&](USceneComponent* Root, const FVector& Palm, double Side, bool bSingleGrip)
	{
		const FVector Wrist = Palm + FVector(-1.8, Side * 1.7, -4.);
		const FVector Elbow = Wrist + FVector(-27., Side * (bSingleGrip ? 14. : 9.), -25.);
		Span(Root, Sleeve, Elbow, Wrist, 7.5f);
		Span(Root, Rubber, FMath::Lerp(Elbow, Wrist, .83), Wrist, 7.8f);
		Part(Root, Sphere, Glove, Palm, FVector(5.7, 4.5, 7.2));
		Part(Root, Sphere, Rubber, Palm + FVector(-1.7, Side * .42, .65), FVector(2.9, 3.2, 4.3));
		for (int32 Finger = 0; Finger < 4; ++Finger)
		{
			Part(Root, Sphere, Glove, Palm + FVector(-1.50, -Side * 2.0, 2.15 - Finger * 1.38),
				FVector(4.45, 2.9, 1.5), FRotator(0, Side * 22., 0));
		}
		Part(Root, Sphere, Glove, Palm + FVector(-1.2, -Side * 2.5, 3.0), FVector(4.5, 2.2, 2.2),
			FRotator(-29, -Side * 26., 0));
	};

	const FRotator AlongView(90, 0, 0);
	Part(RadioModel, Cube, Rubber, FVector(.05, 0, 0), FVector(5.7, 5.65, 13.2));
	for (const double Side : {-1., 1.})
	{
		Part(RadioModel, Cube, Rubber, FVector(.05, Side * 3.2, 0), FVector(5.66, .78, 11.62));
		for (const double End : {-1., 1.})
			Part(RadioModel, Cylinder, Rubber, FVector(.05, Side * 2.82, End * 5.81),
				FVector(1.57, 1.57, 5.69), AlongView);
	}
	Part(RadioModel, Cube, Housing, FVector(-.65, 0, .25), FVector(4.8, 6.65, 12.55));
	Part(RadioModel, Cube, Rubber, FVector(-2.85, 0, 2.3), FVector(.45, 5.85, 4.45));
	Part(RadioModel, Cube, Screen, FVector(-3.12, 0, 2.6), FVector(.12, 4.85, 2.45));
	for (int32 Bar = 0; Bar < 4; ++Bar)
	{
		const double Height = .25 + Bar * .22;
		Part(RadioModel, Cube, Signal, FVector(-3.21, .55 + Bar * .42, 2.03 + Height * .5),
			FVector(.08, .20, Height));
	}
	for (int32 Slot = 0; Slot < 5; ++Slot)
	{
		Part(RadioModel, Cube, Rubber, FVector(-3.08, -.22, .05 - Slot * .52), FVector(.25, 4.55, .22));
	}
	for (const double Y : {-1.53, 0., 1.53})
	{
		Part(RadioModel, Cube, Metal, FVector(-3.06, Y, -3.82), FVector(.27, 1.08, .79));
	}
	Part(RadioModel, Cube, Rubber, FVector(-.8, 3.49, .7), FVector(2.95, .81, 3.3));
	Part(RadioModel, Cylinder, Metal, FVector(.55, 1.89, 7.05), FVector(2.1, 2.1, 1.4));
	Part(RadioModel, Cylinder, Rubber, FVector(.55, -2.16, 7.13), FVector(1.84, 1.84, 1.65));
	Part(RadioModel, Cylinder, Rubber, FVector(.55, -2.16, 12.32), FVector(.69, .69, 9.5));
	Part(RadioModel, Sphere, Rubber, FVector(.55, -2.16, 17.05), FVector(.7, .7, .7));
	Hand(RadioModel, FVector(-.05, 4.35, -4.2), 1.f, true);

	Part(BinocularModel, Cylinder, Housing, FVector(.35, 0, -.4), FVector(3.55, 3.55, 11.25), AlongView);
	Part(BinocularModel, Cylinder, Metal, FVector(-2, 0, 2.55), FVector(2.8, 2.8, 1.15));
	for (const double Side : {-1., 1.})
	{
		const double Y = Side * 5.85;
		Part(BinocularModel, Cylinder, Housing, FVector(1.7, Y, 0), FVector(8.46, 8.46, 12.5), AlongView);
		Part(BinocularModel, Cylinder, Rubber, FVector(-4.8, Y, 0), FVector(9.25, 9.25, 3.7), AlongView);
		Part(BinocularModel, Cylinder, Metal, FVector(-6.6, Y, 0), FVector(7.89, 7.89, .37), AlongView);
		Part(BinocularModel, Cylinder, Glass, FVector(-6.83, Y, 0), FVector(7.1, 7.1, .28), AlongView);
		Part(BinocularModel, Cylinder, Rubber, FVector(7.6, Y, 0), FVector(9.38, 9.38, 2.35), AlongView);
		Part(BinocularModel, Cylinder, Glass, FVector(8.82, Y, 0), FVector(7.62, 7.62, .36), AlongView);
		for (const double Rib : {-1.25, .2, 1.65, 3.1})
		{
			Part(BinocularModel, Cylinder, Rubber, FVector(Rib, Y, 0), FVector(8.64, 8.64, .41), AlongView);
		}
		Hand(BinocularModel, FVector(.8, Side * 10.1, -2.75), Side, false);
	}
}

void AYellCommander::ResetEquipment()
{
	ActiveEquipment = EYellEquipment::None;
	EquipmentLift = 0.f;
	Optics = 0.f;
	ShowModel(*RadioModel, false);
	ShowModel(*BinocularModel, false);
	View->SetFieldOfView(StandardFOV);
}

void AYellCommander::UpdateEquipment(const EYellEquipment Requested, const float DeltaTime)
{
	if (ActiveEquipment == EYellEquipment::None)
	{
		if (Requested == EYellEquipment::None) return;
		ActiveEquipment = Requested;
	}
	const bool bRaising = ActiveEquipment == Requested;
	const bool bRadio = ActiveEquipment == EYellEquipment::Radio;
	const float Duration = bRaising ? (bRadio ? .27f : .41f) : .24f;
	EquipmentLift = FMath::FInterpConstantTo(EquipmentLift, bRaising ? 1.f : 0.f, DeltaTime, 1.f / Duration);
	if (!bRaising && EquipmentLift <= 0.f)
	{
		ResetEquipment();
		return;
	}

	const double Ease = FMath::SmoothStep(0., 1., static_cast<double>(EquipmentLift));
	const double Arc = 3. * FMath::Sin(UE_PI * Ease);
	const double Motion = FMath::Clamp(GetVelocity().Size2D() / 640., 0., 1.);
	const double Sway = FMath::Sin(GetWorld()->GetTimeSeconds() * 13.) * .55 * Motion;
	Optics = bRadio ? 0.f : FMath::SmoothStep(.64f, .94f, EquipmentLift);
	View->SetFieldOfView(FMath::Lerp(StandardFOV, OpticFOV, Optics));
	ShowModel(*RadioModel, bRadio);
	ShowModel(*BinocularModel, !bRadio && EquipmentLift < .91f);
	if (bRadio)
	{
		const FVector Location = FMath::Lerp(FVector(48, 31, -49), FVector(43, 25, -13), Ease);
		RadioModel->SetRelativeLocationAndRotation(Location + FVector(0, Sway, Arc),
			FMath::Lerp(FRotator(-27, 5, 13), FRotator(-8, 20, -6), Ease));
	}
	else
	{
		const FVector Location = FMath::Lerp(FVector(55, 0, -51), FVector(12, 0, 0), Ease);
		BinocularModel->SetRelativeLocationAndRotation(Location + FVector(0, Sway, Arc * .45),
			FMath::Lerp(FRotator(-19, 0, -4), FRotator::ZeroRotator, Ease));
	}
}
