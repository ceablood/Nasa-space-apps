using UnrealBuildTool;

public class KozmogenisEditorTarget : TargetRules
{
	public KozmogenisEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_4;
		ExtraModuleNames.Add("Kozmogenis");
	}
}
