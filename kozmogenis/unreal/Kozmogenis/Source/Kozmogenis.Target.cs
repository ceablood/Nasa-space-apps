using UnrealBuildTool;

public class KozmogenisTarget : TargetRules
{
	public KozmogenisTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		ExtraModuleNames.Add("Kozmogenis");
	}
}
