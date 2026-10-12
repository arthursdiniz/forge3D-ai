// Research-only validator. This is never installed into the Forge3D product.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

public static class UnityResearchValidation
{
    [Serializable] public class Config { public string outputRoot; public string summaryPath; public Case[] cases; public LODChain[] lodChains; }
    [Serializable] public class Case { public string name; public string folder; public string model; public int expectedTriangles; public float[] expectedUnityDimensions; }
    [Serializable] public class LODChain { public string name; public string[] cases; public float[] thresholds; }
    [Serializable] public class Manifest { public string editor_class; public string model; public string albedo; public string provider; }
    [Serializable] public class MeshReport
    {
        public string name; public int vertices; public int triangles; public int submeshes;
        public int uvCount; public int normalCount; public int tangentCount;
        public bool finiteVertices; public bool finiteUVs; public bool finiteNormals; public bool finiteTangents;
        public int zeroNormals; public int zeroTangents; public int uvOutsideUnitSquare;
        public int degenerateTriangles; public int zeroAreaTriangles; public double degenerateAreaToleranceLocalUnits; public long runtimeMemoryBytes; public string indexFormat;
    }
    [Serializable] public class MaterialReport
    {
        public string name; public string shader; public bool shaderSupported; public bool urpLit;
        public float metallic; public float smoothness; public string albedo;
        public int textureWidth; public int textureHeight; public bool albedoSRGB; public long textureRuntimeMemoryBytes;
    }
    [Serializable] public class RenderReport
    {
        public string view; public bool passed; public string png; public string error;
        public int width; public int height; public int nonBackgroundPixels; public int magentaPixels;
        public double editorRenderMilliseconds;
    }
    [Serializable] public class CaseReport
    {
        public string name; public bool imported; public bool geometryPassed; public bool importCompatibilityPassed; public bool surfaceCleanlinessPassed; public bool materialPassed;
        public bool originalPackageImporterInvoked; public string provider; public string error;
        public string sourceFBX; public long fbxBytes; public string fbxSHA256; public string originalPrefab; public string researchPrefab;
        public int meshCount; public int vertexCount; public int triangles; public float[] dimensions;
        public bool expectedTriangleCountMatches; public bool expectedDimensionsMatch;
        public MeshReport[] meshes; public MaterialReport[] materials; public RenderReport[] renders;
        public bool prefabReloaded; public bool boxColliderPresent; public float[] boxColliderSize;
        public float[] boxColliderWorldBoundsSize; public float[] rootScale; public string[] warnings;
        public bool boxColliderRaycastHit; public bool boxColliderBoundsMatch; public int lodLevels; public int lod0Triangles; public bool lodHasReducedGeometry;
        public string colliderScope = "One bounds BoxCollider added by research validator. No mesh collider cooking, rigidbody, collision fidelity, or gameplay test.";
        public string lodScope = "One LOD0 plus culling below 2% screen height. No simplified LOD mesh or runtime performance gain demonstrated.";
    }
    [Serializable] public class Report
    {
        public string unityVersion; public string urpVersion = "17.3.0"; public string graphicsDevice;
        public string utc; public bool passed; public CaseReport[] cases; public LODReport[] lodChains;
        public bool originalControlFailedAsExpected; public bool allGeneratedImportCompatibilityPassed; public bool allGeneratedSurfaceCleanlinessPassed;
        public int generatedPackageCount; public int successfulPackageImports;
        public string scope = "Actual Unity FBX/package import, geometry arrays, URP materials, prefab serialization, simple collider raycast, LOD component, and 512px editor renders. No standalone player, animation, target-platform frame time, VRAM benchmark, or gameplay quality assessment.";
    }
    [Serializable] public class LODLevelReport
    {
        public string sourceCase; public int triangles; public int vertices; public int renderers; public float screenRelativeTransitionHeight; public float[] dimensions;
    }
    [Serializable] public class LODReport
    {
        public string name; public bool passed; public string error; public string prefab; public string unityPackage; public long unityPackageBytes; public string unityPackageSHA256; public string[] unityPackageAssetPaths; public LODLevelReport[] levels;
        public bool descendingTriangleCounts; public bool allSourceGeometryChecksPassed; public bool prefabReloaded; public int[] reloadedTriangleCounts;
        public bool boxColliderRaycastHit; public bool boxColliderBoundsMatch; public float[] dimensions;
        public RenderReport[] forcedLevelRenders;
        public string scope = "Research prefab using the exported high/medium/low meshes in a real 3-level LODGroup. Thresholds are illustrative. Serialization and forced-level editor renders are tested; camera transition behavior, device/player frame time, gameplay collisions and perceptual LOD quality are not profiled.";
    }

    public static void BatchValidate()
    {
        try
        {
            string[] args = Environment.GetCommandLineArgs();
            int at = Array.IndexOf(args, "-researchConfig");
            if (at < 0 || at + 1 >= args.Length) throw new ArgumentException("Missing -researchConfig.");
            Config config = JsonUtility.FromJson<Config>(File.ReadAllText(args[at + 1]));
            Directory.CreateDirectory(config.outputRoot);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EnsureURP();
            var reports = new List<CaseReport>();
            foreach (Case item in config.cases)
            {
                CaseReport report = Validate(item, config.outputRoot);
                reports.Add(report);
                File.WriteAllText(Path.Combine(config.outputRoot, item.name + ".json"), JsonUtility.ToJson(report, true));
                Debug.Log("RESEARCH_UNITY_CASE " + JsonUtility.ToJson(report));
            }
            var lodReports = new List<LODReport>();
            foreach (LODChain chain in config.lodChains ?? new LODChain[0])
            {
                LODReport lodReport = ValidateLODChain(chain, reports, config.outputRoot);
                lodReports.Add(lodReport);
                File.WriteAllText(Path.Combine(config.outputRoot, chain.name + ".json"), JsonUtility.ToJson(lodReport, true));
                Debug.Log("RESEARCH_UNITY_LOD " + JsonUtility.ToJson(lodReport));
            }
            Report summary = new Report { unityVersion = Application.unityVersion, graphicsDevice = SystemInfo.graphicsDeviceName,
                utc = DateTime.UtcNow.ToString("o"), cases = reports.ToArray(), lodChains = lodReports.ToArray(),
                passed = reports.All(r => r.imported && r.geometryPassed && r.materialPassed && r.prefabReloaded && r.boxColliderPresent && r.boxColliderRaycastHit && r.boxColliderBoundsMatch && r.renders != null && r.renders.All(v => v.passed)) && lodReports.All(r => r.passed) };
            var generated = reports.Where(r => r.originalPackageImporterInvoked).ToArray();
            var originalControl = reports.FirstOrDefault(r => r.name == "ground_truth");
            summary.originalControlFailedAsExpected = originalControl != null && originalControl.imported && !originalControl.expectedTriangleCountMatches && !originalControl.geometryPassed;
            summary.generatedPackageCount = generated.Length;
            summary.successfulPackageImports = generated.Count(r => r.imported && r.importCompatibilityPassed && r.materialPassed);
            summary.allGeneratedImportCompatibilityPassed = generated.Length > 0 && generated.All(r => r.imported && r.importCompatibilityPassed && r.materialPassed && r.prefabReloaded && r.boxColliderBoundsMatch && r.boxColliderRaycastHit && r.renders.All(v => v.passed));
            summary.allGeneratedSurfaceCleanlinessPassed = generated.Length > 0 && generated.All(r => r.surfaceCleanlinessPassed);
            string summaryJson = JsonUtility.ToJson(summary, true);
            File.WriteAllText(Path.Combine(config.outputRoot, "unity-validation.json"), summaryJson);
            if (!string.IsNullOrEmpty(config.summaryPath)) File.WriteAllText(config.summaryPath, summaryJson);
            Debug.Log("RESEARCH_UNITY_COMPLETE passed=" + summary.passed);
            EditorApplication.Exit(summary.passed ? 0 : 1);
        }
        catch (Exception error) { Debug.LogException(error); EditorApplication.Exit(2); }
    }

    static void EnsureURP()
    {
        Directory.CreateDirectory("Assets/ResearchGenerated");
        AssetDatabase.Refresh();
        const string rendererPath = "Assets/ResearchGenerated/ResearchRenderer.asset";
        const string pipelinePath = "Assets/ResearchGenerated/ResearchURP.asset";
        var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
        if (renderer == null) { renderer = ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(renderer, rendererPath); }
        var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(pipelinePath);
        if (pipeline == null) { pipeline = UniversalRenderPipelineAsset.Create(renderer); AssetDatabase.CreateAsset(pipeline, pipelinePath); }
        GraphicsSettings.defaultRenderPipeline = pipeline;
        QualitySettings.renderPipeline = pipeline;
        AssetDatabase.SaveAssets();
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(.6f, .6f, .6f);
        var lightObject = new GameObject("ResearchKeyLight");
        var light = lightObject.AddComponent<Light>();
        light.type = LightType.Directional; light.intensity = 2.2f; light.shadows = LightShadows.None;
        lightObject.transform.rotation = Quaternion.Euler(35, -30, 0);
    }

    static CaseReport Validate(Case item, string outputRoot)
    {
        var report = new CaseReport { name = item.name, expectedTriangleCountMatches = true, expectedDimensionsMatch = true };
        GameObject instance = null;
        var warnings = new List<string>();
        Application.LogCallback warningCallback = (message, stack, type) => { if (type == LogType.Warning) warnings.Add(message); };
        Application.logMessageReceived += warningCallback;
        try
        {
            string manifestPath = Path.Combine(item.folder, "asset_manifest.json");
            Manifest manifest = File.Exists(manifestPath) ? JsonUtility.FromJson<Manifest>(File.ReadAllText(manifestPath)) : null;
            report.provider = manifest != null ? manifest.provider : "procedural-ground-truth";
            string modelPath = (item.folder + "/" + (manifest != null ? manifest.model : item.model)).Replace('\\', '/');
            report.sourceFBX = Path.GetFullPath(modelPath); report.fbxBytes = new FileInfo(modelPath).Length;
            using (var algorithm = SHA256.Create()) using (var stream = File.OpenRead(modelPath)) report.fbxSHA256 = BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            string prefabPath = item.folder + "/Prefabs/Forge3D.prefab";
            if (manifest != null && !string.IsNullOrEmpty(manifest.editor_class))
            {
                Type importer = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(manifest.editor_class)).FirstOrDefault(t => t != null);
                if (importer == null) throw new InvalidOperationException("Package importer not compiled: " + manifest.editor_class);
                report.originalPackageImporterInvoked = true;
                try { importer.GetMethod("ImportPackage", BindingFlags.Static | BindingFlags.Public).Invoke(null, new object[] { item.folder }); }
                catch (TargetInvocationException exception) { throw exception.InnerException ?? exception; }
                report.originalPrefab = prefabPath;
                instance = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath));
            }
            else
            {
                AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceSynchronousImport);
                var modelImporter = (ModelImporter)AssetImporter.GetAtPath(modelPath);
                modelImporter.globalScale = 1; modelImporter.useFileScale = true; modelImporter.bakeAxisConversion = true;
                modelImporter.importNormals = ModelImporterNormals.Import; modelImporter.importTangents = ModelImporterTangents.CalculateMikk;
                modelImporter.importAnimation = false; modelImporter.isReadable = true; modelImporter.SaveAndReimport();
                instance = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(modelPath));
                ConvertFixtureMaterials(instance, item.name);
            }
            if (instance == null) throw new InvalidOperationException("No GameObject after FBX import.");
            // CPU arrays are inspected in the Editor; this does not establish player read/write settings.
            report.imported = true;
            instance.name = item.name;
            var filters = instance.GetComponentsInChildren<MeshFilter>(true);
            report.meshes = filters.Select(f => InspectMesh(f.sharedMesh)).ToArray();
            report.meshCount = report.meshes.Length; report.triangles = report.meshes.Sum(m => m.triangles); report.vertexCount = report.meshes.Sum(m => m.vertices);
            var renderers = instance.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) throw new InvalidOperationException("No renderers.");
            Bounds bounds = renderers[0].bounds;
            foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
            report.dimensions = new[] { bounds.size.x, bounds.size.y, bounds.size.z };
            if (item.expectedTriangles > 0) report.expectedTriangleCountMatches = report.triangles == item.expectedTriangles;
            if (item.expectedUnityDimensions != null && item.expectedUnityDimensions.Length == 3)
                for (int i = 0; i < 3; i++) report.expectedDimensionsMatch &= Mathf.Abs(report.dimensions[i] - item.expectedUnityDimensions[i]) <= Mathf.Max(.001f, item.expectedUnityDimensions[i] * .01f);
            report.importCompatibilityPassed = report.triangles > 0 && report.expectedTriangleCountMatches && report.expectedDimensionsMatch && report.meshes.All(m => m.finiteVertices && m.finiteUVs && m.finiteNormals && m.finiteTangents && m.uvCount == m.vertices && m.normalCount == m.vertices && m.zeroNormals == 0);
            report.surfaceCleanlinessPassed = report.meshes.All(m => m.degenerateTriangles == 0);
            report.geometryPassed = report.importCompatibilityPassed && report.surfaceCleanlinessPassed;
            report.materials = renderers.SelectMany(r => r.sharedMaterials).Where(m => m != null).Distinct().Select(InspectMaterial).ToArray();
            report.materialPassed = report.materials.Length > 0 && report.materials.All(m => m.urpLit && m.shaderSupported);
            if (manifest != null && !string.IsNullOrEmpty(manifest.albedo)) report.materialPassed &= report.materials.Any(m => m.textureWidth > 0 && m.albedoSRGB);
            if (manifest != null && string.IsNullOrEmpty(manifest.albedo)) report.materialPassed &= report.materials.All(m => m.textureWidth == 0);
            var box = instance.AddComponent<BoxCollider>();
            var localBounds = new Bounds(instance.transform.InverseTransformPoint(bounds.min), Vector3.zero);
            // FBX roots can have both a 100x scale and a 90-degree axis rotation.
            for (int i = 0; i < 8; i++) localBounds.Encapsulate(instance.transform.InverseTransformPoint(new Vector3((i & 1) == 0 ? bounds.min.x : bounds.max.x, (i & 2) == 0 ? bounds.min.y : bounds.max.y, (i & 4) == 0 ? bounds.min.z : bounds.max.z)));
            box.center = localBounds.center; box.size = localBounds.size;
            Physics.SyncTransforms();
            report.boxColliderBoundsMatch = Vector3.Distance(box.bounds.size, bounds.size) < .0001f && Vector3.Distance(box.bounds.center, bounds.center) < .0001f;
            report.boxColliderRaycastHit = box.Raycast(new Ray(bounds.center + Vector3.forward * (bounds.size.magnitude + 1), Vector3.back), out RaycastHit hit, bounds.size.magnitude * 3 + 2);
            var group = instance.AddComponent<LODGroup>();
            group.SetLODs(new[] { new LOD(.02f, renderers) }); group.RecalculateBounds();
            report.lodLevels = group.lodCount; report.lod0Triangles = report.triangles; report.lodHasReducedGeometry = false;
            report.researchPrefab = "Assets/ResearchGenerated/" + item.name + ".prefab";
            PrefabUtility.SaveAsPrefabAsset(instance, report.researchPrefab);
            AssetDatabase.SaveAssets();
            var reload = AssetDatabase.LoadAssetAtPath<GameObject>(report.researchPrefab);
            report.prefabReloaded = reload != null && reload.GetComponentsInChildren<MeshFilter>(true).Length == filters.Length;
            var reloadedBox = reload.GetComponent<BoxCollider>();
            report.boxColliderPresent = reloadedBox != null;
            report.boxColliderSize = reloadedBox == null ? null : new[] { reloadedBox.size.x, reloadedBox.size.y, reloadedBox.size.z };
            report.boxColliderWorldBoundsSize = new[] { box.bounds.size.x, box.bounds.size.y, box.bounds.size.z };
            report.rootScale = new[] { instance.transform.lossyScale.x, instance.transform.lossyScale.y, instance.transform.lossyScale.z };
            var views = new[] { "front", "three_quarter", "side", "rear" };
            var directions = new[] { new Vector3(0, .03f, 1), new Vector3(.6f, .44f, .8f), new Vector3(1, .03f, 0), new Vector3(0, .03f, -1) };
            report.renders = views.Select((view, index) => Render(instance, bounds, view, directions[index], outputRoot, item.name)).ToArray();
        }
        catch (Exception error) { report.error = error.ToString(); Debug.LogException(error); }
        finally { Application.logMessageReceived -= warningCallback; report.warnings = warnings.Distinct().ToArray(); if (instance != null) Object.DestroyImmediate(instance); }
        return report;
    }

    static LODReport ValidateLODChain(LODChain chain, List<CaseReport> reports, string outputRoot)
    {
        var result = new LODReport { name = chain.name, prefab = "Assets/ResearchGenerated/" + chain.name + ".prefab" };
        GameObject root = null;
        try
        {
            if (chain.cases.Length != 3 || chain.thresholds.Length != 3) throw new ArgumentException("LOD research chain requires 3 cases and 3 thresholds.");
            root = new GameObject(chain.name);
            var levels = new List<LODLevelReport>();
            var lods = new List<LOD>();
            Bounds highBounds = new Bounds();
            for (int index = 0; index < chain.cases.Length; index++)
            {
                var source = reports.Single(r => r.name == chain.cases[index]);
                if (!source.imported || !source.importCompatibilityPassed || !source.materialPassed || string.IsNullOrEmpty(source.originalPrefab)) throw new InvalidOperationException("LOD source package not import-compatible: " + source.name);
                var child = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(source.originalPrefab));
                child.name = "LOD" + index + "_" + source.name; child.transform.SetParent(root.transform, false);
                Renderer[] renderers = child.GetComponentsInChildren<Renderer>(true);
                Bounds bounds = renderers[0].bounds;
                foreach (Renderer renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
                if (index == 0) highBounds = bounds;
                MeshFilter[] filters = child.GetComponentsInChildren<MeshFilter>(true);
                levels.Add(new LODLevelReport { sourceCase = source.name, triangles = filters.Sum(f => f.sharedMesh.triangles.Length / 3),
                    vertices = filters.Sum(f => f.sharedMesh.vertexCount), renderers = renderers.Length,
                    screenRelativeTransitionHeight = chain.thresholds[index], dimensions = new[] { bounds.size.x, bounds.size.y, bounds.size.z } });
                lods.Add(new LOD(chain.thresholds[index], renderers));
            }
            result.levels = levels.ToArray(); result.descendingTriangleCounts = levels[0].triangles > levels[1].triangles && levels[1].triangles > levels[2].triangles;
            result.allSourceGeometryChecksPassed = chain.cases.All(name => reports.Single(r => r.name == name).geometryPassed);
            var group = root.AddComponent<LODGroup>(); group.SetLODs(lods.ToArray()); group.RecalculateBounds();
            var collider = root.AddComponent<BoxCollider>(); collider.center = highBounds.center; collider.size = highBounds.size;
            Physics.SyncTransforms();
            result.boxColliderRaycastHit = collider.Raycast(new Ray(highBounds.center + Vector3.forward * (highBounds.size.magnitude + 1), Vector3.back), out RaycastHit hit, highBounds.size.magnitude * 3 + 2);
            result.boxColliderBoundsMatch = Vector3.Distance(collider.bounds.size, highBounds.size) < .0001f && Vector3.Distance(collider.bounds.center, highBounds.center) < .0001f;
            result.dimensions = new[] { highBounds.size.x, highBounds.size.y, highBounds.size.z };
            PrefabUtility.SaveAsPrefabAsset(root, result.prefab); AssetDatabase.SaveAssets();
            var loaded = AssetDatabase.LoadAssetAtPath<GameObject>(result.prefab);
            var reloadedGroup = loaded == null ? null : loaded.GetComponent<LODGroup>();
            result.prefabReloaded = reloadedGroup != null && reloadedGroup.lodCount == 3;
            result.reloadedTriangleCounts = reloadedGroup.GetLODs().Select(lod => lod.renderers.Sum(renderer => renderer.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3)).ToArray();
            result.prefabReloaded &= result.reloadedTriangleCounts.SequenceEqual(levels.Select(level => level.triangles));
            var renders = new List<RenderReport>();
            for (int index = 0; index < levels.Count; index++)
            {
                group.ForceLOD(index);
                renders.Add(Render(root, highBounds, "LOD" + index + "_three_quarter", new Vector3(.6f, .44f, .8f), outputRoot, chain.name));
            }
            group.ForceLOD(-1);
            result.forcedLevelRenders = renders.ToArray();
            result.passed = result.descendingTriangleCounts && result.prefabReloaded && result.boxColliderRaycastHit && result.boxColliderBoundsMatch && result.forcedLevelRenders.All(render => render.passed);
            if (result.passed)
            {
                result.unityPackage = Path.Combine(outputRoot, chain.name + ".unitypackage");
                // IncludeDependencies would also export URP registry package source files.
                // Keep actual prop dependencies under Assets; URP remains a target-project prerequisite.
                result.unityPackageAssetPaths = AssetDatabase.GetDependencies(result.prefab, true).Where(path => path.StartsWith("Assets/", StringComparison.Ordinal)).ToArray();
                AssetDatabase.ExportPackage(result.unityPackageAssetPaths, result.unityPackage, ExportPackageOptions.Default);
                result.unityPackageBytes = new FileInfo(result.unityPackage).Length;
                using (var algorithm = SHA256.Create()) using (var stream = File.OpenRead(result.unityPackage)) result.unityPackageSHA256 = BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
                result.passed &= result.unityPackageBytes > 0;
            }
        }
        catch (Exception error) { result.error = error.ToString(); Debug.LogException(error); }
        finally { if (root != null) Object.DestroyImmediate(root); }
        return result;
    }

    static MeshReport InspectMesh(Mesh mesh)
    {
        var result = new MeshReport { name = mesh.name, vertices = mesh.vertexCount, triangles = mesh.triangles.Length / 3, submeshes = mesh.subMeshCount,
            uvCount = mesh.uv.Length, normalCount = mesh.normals.Length, tangentCount = mesh.tangents.Length, indexFormat = mesh.indexFormat.ToString(),
            finiteVertices = true, finiteUVs = true, finiteNormals = true, finiteTangents = true, runtimeMemoryBytes = Profiler.GetRuntimeMemorySizeLong(mesh) };
        foreach (Vector3 v in mesh.vertices) result.finiteVertices &= Finite(v.x) && Finite(v.y) && Finite(v.z);
        foreach (Vector2 uv in mesh.uv) { result.finiteUVs &= Finite(uv.x) && Finite(uv.y); if (uv.x < -.0001f || uv.x > 1.0001f || uv.y < -.0001f || uv.y > 1.0001f) result.uvOutsideUnitSquare++; }
        foreach (Vector3 n in mesh.normals) { result.finiteNormals &= Finite(n.x) && Finite(n.y) && Finite(n.z); if (n.sqrMagnitude < .0001f) result.zeroNormals++; }
        foreach (Vector4 t in mesh.tangents) { result.finiteTangents &= Finite(t.x) && Finite(t.y) && Finite(t.z) && Finite(t.w); if (new Vector3(t.x, t.y, t.z).sqrMagnitude < .0001f) result.zeroTangents++; }
        Vector3[] vertices = mesh.vertices; int[] triangles = mesh.triangles;
        result.degenerateAreaToleranceLocalUnits = Math.Max(mesh.bounds.size.sqrMagnitude * 1e-12, 1e-30);
        double crossSquaredTolerance = 4 * result.degenerateAreaToleranceLocalUnits * result.degenerateAreaToleranceLocalUnits;
        for (int i = 0; i < triangles.Length; i += 3)
        {
            Vector3 a = vertices[triangles[i + 1]] - vertices[triangles[i]], b = vertices[triangles[i + 2]] - vertices[triangles[i]];
            double x = (double)a.y * b.z - (double)a.z * b.y;
            double y = (double)a.z * b.x - (double)a.x * b.z;
            double z = (double)a.x * b.y - (double)a.y * b.x;
            double crossSquared = x * x + y * y + z * z;
            if (crossSquared == 0) result.zeroAreaTriangles++;
            if (crossSquared <= crossSquaredTolerance) result.degenerateTriangles++;
        }
        return result;
    }
    static bool Finite(float value) { return !float.IsNaN(value) && !float.IsInfinity(value); }

    static MaterialReport InspectMaterial(Material material)
    {
        var texture = material.HasProperty("_BaseMap") ? material.GetTexture("_BaseMap") as Texture2D : null;
        var importer = texture == null ? null : AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) as TextureImporter;
        return new MaterialReport { name = material.name, shader = material.shader.name, shaderSupported = material.shader.isSupported,
            urpLit = material.shader.name == "Universal Render Pipeline/Lit", metallic = material.GetFloat("_Metallic"), smoothness = material.GetFloat("_Smoothness"),
            albedo = texture == null ? null : AssetDatabase.GetAssetPath(texture), textureWidth = texture == null ? 0 : texture.width,
            textureHeight = texture == null ? 0 : texture.height, albedoSRGB = importer != null && importer.sRGBTexture,
            textureRuntimeMemoryBytes = texture == null ? 0 : Profiler.GetRuntimeMemorySizeLong(texture) };
    }

    static void ConvertFixtureMaterials(GameObject instance, string name)
    {
        var mapping = new Dictionary<Material, Material>();
        foreach (var renderer in instance.GetComponentsInChildren<Renderer>())
        {
            renderer.sharedMaterials = renderer.sharedMaterials.Select(original => {
                if (original == null) return new Material(Shader.Find("Universal Render Pipeline/Lit"));
                if (!mapping.TryGetValue(original, out Material material))
                {
                    string materialPath = "Assets/ResearchGenerated/" + name + "_" + mapping.Count + ".mat";
                    material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
                    if (material == null) { material = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(material, materialPath); }
                    Color color = original.HasProperty("_BaseColor") ? original.GetColor("_BaseColor") : original.HasProperty("_Color") ? original.color : new Color(.48f, .22f, .065f, 1);
                    material.SetColor("_BaseColor", color); material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", .35f);
                    EditorUtility.SetDirty(material);
                    mapping.Add(original, material);
                }
                return material;
            }).ToArray();
        }
    }

    static RenderReport Render(GameObject instance, Bounds bounds, string view, Vector3 direction, string outputRoot, string name)
    {
        var report = new RenderReport { view = view, width = 512, height = 512, png = Path.Combine(outputRoot, name + "_" + view + ".png") };
        GameObject cameraObject = null; RenderTexture target = null; Texture2D pixels = null;
        RenderTexture previous = RenderTexture.active;
        try
        {
            cameraObject = new GameObject("ResearchCamera");
            var camera = cameraObject.AddComponent<Camera>();
            camera.enabled = false; camera.orthographic = true; camera.orthographicSize = Mathf.Max(bounds.extents.y, bounds.extents.x, bounds.extents.z) * 1.3f;
            camera.transform.position = bounds.center + direction.normalized * (bounds.size.magnitude * 3 + 1);
            camera.transform.LookAt(bounds.center); camera.nearClipPlane = .01f; camera.farClipPlane = bounds.size.magnitude * 8 + 10;
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.07f, .10f, .12f, 0); camera.allowHDR = false; camera.allowMSAA = false;
            var extra = camera.GetUniversalAdditionalCameraData(); extra.renderPostProcessing = false; extra.renderShadows = false;
            target = new RenderTexture(512, 512, 24, RenderTextureFormat.ARGB32); target.Create(); camera.targetTexture = target;
            var request = new UniversalRenderPipeline.SingleCameraRequest { destination = target };
            if (!RenderPipeline.SupportsRenderRequest(camera, request)) throw new InvalidOperationException("Active URP does not support render request.");
            var timer = Stopwatch.StartNew();
            RenderPipeline.SubmitRenderRequest(camera, request);
            timer.Stop(); report.editorRenderMilliseconds = timer.Elapsed.TotalMilliseconds;
            RenderTexture.active = target; pixels = new Texture2D(512, 512, TextureFormat.RGBA32, false);
            pixels.ReadPixels(new Rect(0, 0, 512, 512), 0, 0); pixels.Apply();
            Color32[] values = pixels.GetPixels32(); Color32 background = values[0];
            foreach (Color32 value in values)
            {
                if (Math.Abs(value.r - background.r) + Math.Abs(value.g - background.g) + Math.Abs(value.b - background.b) > 15) report.nonBackgroundPixels++;
                if (value.r > 180 && value.b > 180 && value.g < 80) report.magentaPixels++;
            }
            File.WriteAllBytes(report.png, pixels.EncodeToPNG());
            report.passed = report.nonBackgroundPixels > 100 && report.magentaPixels == 0;
        }
        catch (Exception error) { report.error = error.ToString(); Debug.LogException(error); }
        finally
        {
            RenderTexture.active = previous;
            if (pixels != null) Object.DestroyImmediate(pixels);
            if (target != null) { target.Release(); Object.DestroyImmediate(target); }
            if (cameraObject != null) Object.DestroyImmediate(cameraObject);
        }
        return report;
    }
}
