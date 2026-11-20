using System.IO;
using UnrealBuildTool;

public class Kozmogenis : ModuleRules
{
	public Kozmogenis(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// KozmoCore: Unreal'den bağımsız, standart C++17 oyun çekirdeği (kozmogenis/core).
		// Kaynakları Private/KozmoCoreUnity.cpp tek derleme birimi olarak içerir; RTTI ve istisna gerektirmez.
		string CoreRoot = Path.GetFullPath(Path.Combine(ModuleDirectory, "..", "..", "..", "..", "core"));
		PublicIncludePaths.Add(Path.Combine(CoreRoot, "include"));
		PublicDefinitions.Add("KOZMO_WITH_UNREAL=1");
		CppStandard = CppStandardVersion.Cpp20;
	}
}
