// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class WarCommanderDemo : ModuleRules
{
	public WarCommanderDemo(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] {
			"AudioCaptureCore", "HTTP", "Json", "NavigationSystem", "SlateCore"
		});

		PublicIncludePaths.AddRange(new string[] {
			"WarCommanderDemo",
			"WarCommanderDemo/Variant_Horror",
			"WarCommanderDemo/Variant_Horror/UI",
			"WarCommanderDemo/Variant_Shooter",
			"WarCommanderDemo/Variant_Shooter/AI",
			"WarCommanderDemo/Variant_Shooter/UI",
			"WarCommanderDemo/Variant_Shooter/Weapons"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
