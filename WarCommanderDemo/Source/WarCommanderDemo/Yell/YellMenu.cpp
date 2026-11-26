#include "YellPlayer.h"

#include "Components/AudioComponent.h"
#include "Brushes/SlateNoResource.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameUserSettings.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Materials/MaterialInterface.h"
#include "Misc/App.h"
#include "Misc/ConfigCacheIni.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"
#include "YellBattle.h"

namespace
{
	constexpr TCHAR Map[] = TEXT("/Game/Yell/ValleAlfa");
	constexpr TCHAR Preferences[] = TEXT("YellCommander");
	const FLinearColor Gold(1.f, .63f, .19f);
	const FLinearColor White(.92f, .94f, .86f);
	const FLinearColor Muted(.69f, .76f, .69f);
	const FLinearColor Carbon(.009f, .016f, .015f);

	const FButtonStyle MenuButton = FButtonStyle()
		.SetNormal(FSlateNoResource()).SetHovered(FSlateNoResource()).SetPressed(FSlateNoResource())
		.SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));

	FLinearColor Alpha(FLinearColor Color, float Opacity)
	{
		Color.A = Opacity;
		return Color;
	}

	void PaintPolygon(FSlateWindowElementList& Output, const FGeometry& Geometry, uint32 Layer,
		TConstArrayView<FVector2f> Points, TConstArrayView<FLinearColor> Colors)
	{
		const auto Resource = FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush("WhiteBrush"));
		TArray<FSlateVertex> Vertices;
		TArray<SlateIndex> Indices;
		Vertices.Reserve(Points.Num());
		Indices.Reserve((Points.Num() - 2) * 3);
		for (int32 Index = 0; Index < Points.Num(); ++Index)
			Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Geometry.GetAccumulatedRenderTransform(),
				Points[Index], FVector2f(.5f, .5f), Colors[Index].ToFColor(true)));
		for (int32 Index = 1; Index < Points.Num() - 1; ++Index)
		{
			Indices.Add(0);
			Indices.Add(Index);
			Indices.Add(Index + 1);
		}
		FSlateDrawElement::MakeCustomVerts(Output, Layer, Resource, Vertices, Indices, nullptr, 0, 0);
	}

	TSharedRef<STextBlock> Text(const TCHAR* Value, const int32 Size, const FLinearColor& Tint, bool bBold = false)
	{
		auto Font = FCoreStyle::GetDefaultFontStyle(bBold ? FName(TEXT("BoldCondensed")) : FName(TEXT("Regular")), Size);
		if (bBold) Font.LetterSpacing = 60;
		return SNew(STextBlock).Text(FText::FromString(Value)).Font(Font).ColorAndOpacity(Tint)
			.ShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, .45f)).ShadowOffset(FVector2D(0., 1.));
	}

	class SYellLogo : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SYellLogo) {}
		SLATE_END_ARGS()

		void Construct(const FArguments&)
		{
			Resource.Reset(LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Game/Yell/Art/Materials/HUD/M_UI_YellCommander.M_UI_YellCommander")));
			if (!Resource.IsValid())
			{
				ChildSlot[Text(TEXT("YELL COMMANDER"), 42, White, true)];
				return;
			}
			Logo.SetResourceObject(Resource.Get());
			Logo.SetImageSize(FVector2f(528.f, 138.f));
			Logo.DrawAs = ESlateBrushDrawType::Image;
			ChildSlot[SNew(SImage).Image(&Logo)];
		}
	private:
		TStrongObjectPtr<UMaterialInterface> Resource;
		FSlateBrush Logo;
	};

	class SYellMenuButton : public SButton
	{
	public:
		SLATE_BEGIN_ARGS(SYellMenuButton) {}
			SLATE_ARGUMENT(FString, Label)
			SLATE_ARGUMENT(bool, Primary)
			SLATE_EVENT(FOnClicked, OnClicked)
		SLATE_END_ARGS()

		void Construct(const FArguments& Args)
		{
			bPrimary = Args._Primary;
			const FLinearColor LabelColor = bPrimary ? FLinearColor(.023f, .015f, .006f) : White;
			const FString Caption = FText::FromString(Args._Label).ToUpper().ToString();
			SButton::Construct(SButton::FArguments().ButtonStyle(&MenuButton)
				.ContentPadding(FMargin(24, 0, 17, 0)).OnClicked(Args._OnClicked)
				.HAlign(HAlign_Fill).VAlign(VAlign_Center)
				[
					SNew(SBox).MinDesiredHeight(63.f)
					[
						SNew(SOverlay)
						+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Center)
						[Text(*Caption, 24, LabelColor, true)]
						+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Center)
						[Text(TEXT("»"), 26, bPrimary ? LabelColor : Gold, true)]
					]
				]);
		}

		int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling,
			FSlateWindowElementList& Output, int32 Layer, const FWidgetStyle& WidgetStyle, bool bEnabled) const override
		{
			const FVector2f Size(Geometry.GetLocalSize());
			const float W = Size.X, H = Size.Y;
			const bool bFocus = IsHovered() || HasKeyboardFocus();
			const bool bPressed = IsPressed();
			const FLinearColor Top = bPrimary ? FLinearColor(1.f, bPressed ? .47f : .72f, bFocus ? .35f : .22f)
				: bFocus ? FLinearColor(.25f, .16f, .042f, .92f) : FLinearColor(.055f, .081f, .067f, .80f);
			const FLinearColor Bottom = bPrimary ? FLinearColor(.63f, bPressed ? .23f : .33f, .032f)
				: bFocus ? FLinearColor(.075f, .056f, .024f, .83f) : FLinearColor(.016f, .029f, .024f, .67f);
			const FLinearColor Stroke = bPrimary ? FLinearColor(1.f, .82f, .42f)
				: bFocus ? Alpha(Gold, .92f) : FLinearColor(.47f, .59f, .47f, .51f);
			const FVector2f Points[] = {{0, 11}, {11, 0}, {W, 0}, {W, H - 11}, {W - 11, H}, {0, H}};
			const FLinearColor Colors[] = {Top, Top, Top, Bottom, Bottom, Bottom};
			PaintPolygon(Output, Geometry, Layer, Points, Colors);
			const TArray<FVector2f> Border = {Points[0], Points[1], Points[2], Points[3], Points[4], Points[5], Points[0]};
			FSlateDrawElement::MakeLines(Output, Layer + 1, Geometry.ToPaintGeometry(), Border, ESlateDrawEffect::None, Stroke, true, 1.f);
			const FVector2f Accent[] = {{0, 11}, {6, 5}, {6, H}, {0, H}};
			const FLinearColor Shine = bPrimary ? White : Stroke;
			const FLinearColor AccentColors[] = {Shine, Shine, Stroke, Stroke};
			PaintPolygon(Output, Geometry, Layer + 1, Accent, AccentColors);
			return SButton::OnPaint(Args, Geometry, Culling, Output, Layer + 2, WidgetStyle, bEnabled);
		}
	private:
		bool bPrimary = false;
	};

	class SYellMenuRoot : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SYellMenuRoot) {}
			SLATE_EVENT(FSimpleDelegate, OnBack)
			SLATE_EVENT(FSimpleDelegate, OnConfirm)
			SLATE_ARGUMENT(bool, DarkenBattle)
			SLATE_DEFAULT_SLOT(FArguments, Content)
		SLATE_END_ARGS()

		void Construct(const FArguments& Args)
		{
			OnBack = Args._OnBack;
			OnConfirm = Args._OnConfirm;
			bDarkenBattle = Args._DarkenBattle;
			ChildSlot[Args._Content.Widget];
		}
		bool SupportsKeyboardFocus() const override { return true; }
		FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override
		{
			if (Event.GetKey() == EKeys::Escape) OnBack.ExecuteIfBound();
			else if ((Event.GetKey() == EKeys::Enter || Event.GetKey() == EKeys::F5) && OnConfirm.IsBound()) OnConfirm.Execute();
			else return FReply::Unhandled();
			return FReply::Handled();
		}

		int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling,
			FSlateWindowElementList& Output, int32 Layer, const FWidgetStyle& Style, bool bEnabled) const override
		{
			const FVector2f Size(Geometry.GetLocalSize());
			const float Columns[] = {0.f, .36f, .75f, 1.f};
			const float Clear[] = {.86f, .69f, .22f, .27f};
			const float Dark[] = {.92f, .80f, .50f, .52f};
			const float* Dimming = bDarkenBattle ? Dark : Clear;
			for (int32 Index = 0; Index < 3; ++Index)
			{
				const float Left = Columns[Index] * Size.X, Right = Columns[Index + 1] * Size.X;
				const FVector2f Points[] = {{Left, 0}, {Right, 0}, {Right, Size.Y}, {Left, Size.Y}};
				const FLinearColor Colors[] = {Alpha(Carbon, Dimming[Index]), Alpha(Carbon, Dimming[Index + 1]),
					Alpha(Carbon, FMath::Min(1.f, Dimming[Index + 1] + .14f)), Alpha(Carbon, FMath::Min(1.f, Dimming[Index] + .14f))};
				PaintPolygon(Output, Geometry, Layer, Points, Colors);
			}
			return SCompoundWidget::OnPaint(Args, Geometry, Culling, Output, Layer + 1, Style, bEnabled);
		}
	private:
		FSimpleDelegate OnBack;
		FSimpleDelegate OnConfirm;
		bool bDarkenBattle = false;
	};

	void SavePreference(const TCHAR* Key, const float Value)
	{
		GConfig->SetFloat(Preferences, Key, Value, GGameUserSettingsIni);
		GConfig->Flush(false, GGameUserSettingsIni);
	}

	const TCHAR* DifficultyLabel(EYellDifficulty Difficulty)
	{
		return Difficulty == EYellDifficulty::Easy ? TEXT("Fácil")
			: Difficulty == EYellDifficulty::Hard ? TEXT("Difícil") : TEXT("Normal");
	}
}

void AYellPlayer::LoadMenuPreferences()
{
	float Volume = 1.f;
	GConfig->GetFloat(Preferences, TEXT("Volumen"), Volume, GGameUserSettingsIni);
	GConfig->GetFloat(Preferences, TEXT("Sensibilidad"), Sensitivity, GGameUserSettingsIni);
	FApp::SetVolumeMultiplier(FMath::Clamp(Volume, 0.f, 1.f));
	Sensitivity = FMath::Clamp(Sensitivity, .12f, 1.05f);
}

void AYellPlayer::CloseMenu()
{
	if (MenuView && GEngine && GEngine->GameViewport)
		GEngine->GameViewport->RemoveViewportWidgetContent(MenuView.ToSharedRef());
	MenuView.Reset();
}

void AYellPlayer::StartMatch(const EYellDifficulty Difficulty)
{
	if (bMenuTransition) return;
	bMenuTransition = true;
	SetPause(false);
	const FString Options = FString::Printf(TEXT("YellDifficulty=%s"), FYellRivalPolicy::Name(Difficulty));
	UGameplayStatics::OpenLevel(this, FName(Map), true, Options);
}

void AYellPlayer::ReturnToMenu()
{
	if (bMenuTransition) return;
	bMenuTransition = true;
	SetPause(false);
	UGameplayStatics::OpenLevel(this, FName(Map), true, TEXT("YellMenu=1"));
}

void AYellPlayer::EscapeMenu()
{
	if (bMenuTransition) return;
	if (Console)
	{
		CloseConsole();
		return;
	}
	if (HasMenu())
	{
		BackFromMenu();
		return;
	}
	const auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	if (!Battle || Battle->IsMenuScene() || !GEngine || !GEngine->GameViewport) return;
	if (Battle->Winner() != INDEX_NONE)
	{
		ReturnToMenu();
		return;
	}
	if (bRecording) FinishRecording(EYellVoiceResult::Interrupted);
	if (SetPause(true))
	{
		ResetEquipmentInput();
		if (CurrentReply.IsValid()) CurrentReply->SetPaused(true);
		ShowMenu(EMenuPage::Pause);
	}
}

void AYellPlayer::BackFromMenu()
{
	switch (MenuPage)
	{
	case EMenuPage::Main: break;
	case EMenuPage::Result: ReturnToMenu(); break;
	case EMenuPage::Difficulty:
	case EMenuPage::Settings: ShowMenu(EMenuPage::Main); break;
	case EMenuPage::Pause:
	{
		if (bMenuTransition || !SetPause(false)) return;
		CloseMenu();
		bShowMouseCursor = false;
		SetInputMode(FInputModeGameOnly().SetConsumeCaptureMouseDown(false));
		if (CurrentReply.IsValid()) CurrentReply->SetPaused(false);
		auto Responses = MoveTemp(PausedResponses);
		PausedResponses.Reset();
		for (auto& Process : Responses) Process();
		break;
	}
	default: ShowMenu(EMenuPage::Settings); break;
	}
}

void AYellPlayer::ShowMenu(const EMenuPage Page)
{
	if (!GEngine || !GEngine->GameViewport) return;
	CloseMenu();
	MenuPage = Page;
	const auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>();
	const EYellDifficulty Difficulty = Battle ? Battle->GetDifficulty() : EYellDifficulty::Normal;
	auto Items = SNew(SVerticalBox);
	auto Button = [&Items](const TCHAR* Label, TFunction<void()> Action, bool bPrimary = false)
	{
		Items->AddSlot().AutoHeight().Padding(0, 0, 0, 10)
		[
			SNew(SYellMenuButton).Label(FString(Label)).Primary(bPrimary)
			.OnClicked_Lambda([Action = MoveTemp(Action)] { Action(); return FReply::Handled(); })
		];
	};
	auto Blurb = [&Items](const TCHAR* Value)
	{
		Items->AddSlot().AutoHeight().Padding(3, 0, 3, 10)[Text(Value, 15, Muted)];
	};
	const TCHAR* Heading = TEXT("YELL COMMANDER");
	const TCHAR* Subtitle = TEXT("VALLE ALFA");
	FLinearColor HeadingColor = White;
	switch (Page)
	{
	case EMenuPage::Main:
		Button(TEXT("Jugar"), [this] { ShowMenu(EMenuPage::Difficulty); }, true);
		Button(TEXT("Configuración"), [this] { ShowMenu(EMenuPage::Settings); });
		Button(TEXT("Salir"), [this] { UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false); });
		break;
	case EMenuPage::Difficulty:
		Heading = TEXT("DIFICULTAD");
		Button(TEXT("Fácil"), [this] { StartMatch(EYellDifficulty::Easy); });
		Blurb(TEXT("Informes cada 7 s · Espera una ventaja clara"));
		Button(TEXT("Normal"), [this] { StartMatch(EYellDifficulty::Normal); }, true);
		Blurb(TEXT("Informes cada 3,5 s · Acepta un riesgo moderado"));
		Button(TEXT("Difícil"), [this] { StartMatch(EYellDifficulty::Hard); });
		Blurb(TEXT("Informes cada 1,25 s · Ataca con menor ventaja"));
		break;
	case EMenuPage::Pause:
		Heading = TEXT("PAUSA");
		Subtitle = DifficultyLabel(Difficulty);
		Button(TEXT("Continuar"), [this] { BackFromMenu(); }, true);
		Button(TEXT("Reiniciar"), [this, Difficulty] { StartMatch(Difficulty); });
		Button(TEXT("Volver al menú"), [this] { ReturnToMenu(); });
		break;
	case EMenuPage::Result:
	{
		const bool bVictory = Battle && Battle->Winner() == 0;
		Heading = bVictory ? TEXT("VICTORIA") : TEXT("DERROTA");
		Subtitle = bVictory ? TEXT("NÚCLEO RIVAL DESTRUIDO") : TEXT("NÚCLEO ALIADO DESTRUIDO");
		HeadingColor = bVictory ? Gold : FLinearColor(1.f, .31f, .19f);
		Button(TEXT("Volver al menú principal"), [this] { ReturnAfterBattle(); }, true);
		break;
	}
	case EMenuPage::Settings:
		Heading = TEXT("CONFIGURACIÓN");
		Button(TEXT("Controles"), [this] { ShowMenu(EMenuPage::Controls); });
		Button(TEXT("Gráficos"), [this] { ShowMenu(EMenuPage::Graphics); });
		Button(TEXT("Sonido"), [this] { ShowMenu(EMenuPage::Audio); });
		break;
	case EMenuPage::Controls:
		Heading = TEXT("CONTROLES");
		Blurb(TEXT("WASD   Moverse\nRatón   Mirar\nClic derecho   Mantener para usar binoculares\nEspacio   Saltar\nV   Hablar · soltar para enviar\nT   Escribir una orden\nR   Cambiar canal\nE / F   Refuerzos / médicos en terminal\nEscape   Pausa"));
		Blurb(TEXT("Sensibilidad del ratón"));
		Items->AddSlot().AutoHeight().Padding(5,2,5,12)
		[SNew(SSlider).MinValue(.12f).MaxValue(1.05f).Value(Sensitivity)
			.OnValueChanged_Lambda([this](float Value) { Sensitivity = Value; })
			.OnMouseCaptureEnd_Lambda([this] { SavePreference(TEXT("Sensibilidad"), Sensitivity); })
			.OnControllerCaptureEnd_Lambda([this] { SavePreference(TEXT("Sensibilidad"), Sensitivity); })];
		break;
	case EMenuPage::Graphics:
	{
		Heading = TEXT("GRÁFICOS");
		auto* Settings = GEngine->GetGameUserSettings();
		const TCHAR* Qualities[] = {TEXT("Baja"),TEXT("Media"),TEXT("Alta"),TEXT("Épica"),TEXT("Cinemática")};
		const int32 Current = Settings->GetOverallScalabilityLevel();
		Blurb(*FString::Printf(TEXT("Calidad actual · %s"), Current < 0 ? TEXT("Personalizada") : Qualities[FMath::Clamp(Current, 0, 4)]));
		for (int32 Level = 0; Level < 4; ++Level)
			Button(Qualities[Level], [this, Settings, Level] {
				Settings->SetOverallScalabilityLevel(Level); Settings->ApplyNonResolutionSettings(); Settings->SaveSettings();
				ShowMenu(EMenuPage::Graphics);
			});
		Button(Settings->GetFullscreenMode() == EWindowMode::Windowed ? TEXT("Usar pantalla completa sin bordes") : TEXT("Usar ventana"),
			[this, Settings] {
				Settings->SetFullscreenMode(Settings->GetFullscreenMode() == EWindowMode::Windowed
					? EWindowMode::WindowedFullscreen : EWindowMode::Windowed);
				Settings->ApplySettings(false); Settings->ConfirmVideoMode(); Settings->SaveSettings();
				ShowMenu(EMenuPage::Graphics);
			});
		Button(Settings->IsVSyncEnabled() ? TEXT("VSync activado") : TEXT("VSync desactivado"), [this, Settings] {
			Settings->SetVSyncEnabled(!Settings->IsVSyncEnabled()); Settings->ApplyNonResolutionSettings(); Settings->SaveSettings();
			ShowMenu(EMenuPage::Graphics);
		});
		break;
	}
	case EMenuPage::Audio:
		Heading = TEXT("SONIDO");
		Blurb(TEXT("Volumen general"));
		Items->AddSlot().AutoHeight().Padding(5,4,5,20)
		[SNew(SSlider).Value(FApp::GetVolumeMultiplier())
			.OnValueChanged_Lambda([](float Value) { FApp::SetVolumeMultiplier(Value); })
			.OnMouseCaptureEnd_Lambda([] { SavePreference(TEXT("Volumen"), FApp::GetVolumeMultiplier()); })
			.OnControllerCaptureEnd_Lambda([] { SavePreference(TEXT("Volumen"), FApp::GetVolumeMultiplier()); })];
		break;
	}
	if (Page != EMenuPage::Main && Page != EMenuPage::Pause && Page != EMenuPage::Result)
		Button(TEXT("Volver"), [this] { BackFromMenu(); });
	auto Content = SNew(SVerticalBox);
	if (Page == EMenuPage::Main)
	{
		Content->AddSlot().AutoHeight().Padding(0, 0, 0, 32)
		[SNew(SBox).HeightOverride(147)[SNew(SYellLogo)]];
	}
	else
	{
		const FString Section = FText::FromString(Subtitle).ToUpper().ToString();
		Content->AddSlot().AutoHeight().Padding(0, 0, 0, 8)[Text(*Section, 16, Gold, true)];
		Content->AddSlot().AutoHeight().Padding(0, 0, 0, 13)[Text(Heading, 53, HeadingColor, true)];
		Content->AddSlot().AutoHeight().HAlign(HAlign_Left).Padding(0, 0, 0, 23)
		[SNew(SBox).WidthOverride(110).HeightOverride(2)
			[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Alpha(Gold, .6f))]];
	}
	Content->AddSlot().FillHeight(1)
		[SNew(SScrollBox) + SScrollBox::Slot()[Items]];
	FSimpleDelegate Confirm;
	if (Page == EMenuPage::Result) Confirm.BindUObject(this, &AYellPlayer::ReturnAfterBattle);
	MenuView = SNew(SYellMenuRoot).OnBack(FSimpleDelegate::CreateUObject(this, &AYellPlayer::EscapeMenu))
		.OnConfirm(Confirm).DarkenBattle(Page == EMenuPage::Pause || Page == EMenuPage::Result)
	[
		SNew(SBox).HAlign(HAlign_Left).VAlign(VAlign_Center).Padding(FMargin(68, 24))
		[
			SNew(SBox).WidthOverride(Page == EMenuPage::Main ? 560.f : 510.f).MaxDesiredHeight(720.f)[Content]
		]
	];
	GEngine->GameViewport->AddViewportWidgetContent(MenuView.ToSharedRef(), 30);
	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(MenuView);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(Mode);
	bShowMouseCursor = true;
}
