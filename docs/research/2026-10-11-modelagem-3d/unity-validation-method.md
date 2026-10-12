# Disposable Unity validation method

Research date: 2026-10-11. No product source, product configuration, or installation under `C:/Projetos/forge3d-ai` is changed by this test.

`data/research-2026-10-11/UnityValidation` is a new Unity 6000.3.0f1 project. Its starting ProjectSettings and package lock were copied read-only from the existing validation project; no Library or asset cache was copied. It uses URP 17.3.0 and the built-in JSON, image conversion and physics modules. All assets and components created by the validator are disposable research artifacts.

The controlled fixture is a deterministic Blender chair. The original FBX exports polygons with 1,092 Blender tessellation triangles. Unity discarded self-intersecting polygons and imported 714 triangles in the initial test, so the original is retained as a failing triangle-fidelity control. A second `ground_truth_clean.fbx` has 214 triangles after research-only cleanup and is tested separately. Both have expected Unity bounds `(0.88, 1.62, 0.82)` metres. Neither is an AI output or demonstrates neural model quality. The original 512px reference PNGs remain unchanged.

For each generated package the validator calls the original package's `manifest.editor_class.ImportPackage` in Unity. It preserves that importer report and prefab. Independently, it reads the imported FBX's mesh arrays, counts vertices/triangles/submeshes, checks finite positions/UVs/normals/tangents, counts zero normals/tangents, UVs outside the unit square and degenerate faces, and records the source FBX SHA256. Degenerate face area tolerance is the squared local mesh bounds diagonal times 1e-12, with double-precision cross-product arithmetic; it scales with FBX local units. Bounds and triangles are checked against the exporter manifest; Unity Y-up bounds correspond to Blender `(x,z,y)`. Import warnings are retained in the report.

`importCompatibilityPassed` checks nonempty meshes, matching dimensions/triangle counts, complete UVs/normals and finite arrays/nonzero normals. `surfaceCleanlinessPassed` separately requires zero faces at or below the scale-relative area tolerance. `zeroAreaTriangles` records exact zero area; `degenerateTriangles` also includes near-zero area. `geometryPassed` requires both compatibility and cleanliness. A serialized LOD setup can pass with an import-compatible high mesh while reporting `allSourceGeometryChecksPassed=false` when its surface-cleanliness check finds tiny faces. The initial high SG import retained all 319,266 triangles but flagged two near-zero-area faces, while medium/low flagged none; this is retained as a diagnostic rather than hidden by the LOD test.

Materials are inspected for the active URP Lit shader and its support on the editor graphics device. Textured packages must retain a nonempty sRGB albedo texture; geometry-only packages must have no albedo assigned. Texture dimensions and Unity-reported texture/mesh memory are recorded. These memory values describe the editor's imported objects; they are not a target-platform GPU budget or standalone player measurement.

A separate research prefab receives one bounds BoxCollider and one LOD0, culled below 2% relative screen height. The prefab is saved and reloaded. A direct `Collider.Raycast` checks that the bounds proxy is usable. Both the collider's local size and its world bounds are recorded, along with root scale, because an FBX can use a 100× root transform. The box encloses holes and can be a poor gameplay collision shape. There is no Rigidbody integration, mesh-collider cooking, physics simulation, animation, navigation or interaction test. A one-level LODGroup is component setup, with no reduced mesh and no demonstrated performance improvement.

The collider's local bounds are derived by transforming all eight world bounding-box corners through the root inverse transform. This accounts for the imported FBX root's axis rotation as well as scale. A separate comparison checks that the collider's world bounds match the renderer bounds; a ray hit alone would not establish correct proxy dimensions.

When `sg_three_quarter`, `sg_best_medium` and `sg_best_low` are present, a separate `sg_best_lod` research prefab combines their original package prefabs into three genuine LOD levels. The thresholds `(0.60, 0.25, 0.05)` are illustrative. The validator checks descending triangle counts, saves/reloads all renderer references and triangle counts, attaches a bounds proxy collider, and renders each level with `LODGroup.ForceLOD`. This demonstrates serialized LOD setup using reduced meshes, with no camera-transition assessment, standalone player frame-time benchmark or claimed visual equivalence across levels.

After the LOD setup checks pass, Unity exports the prefab with its mesh/material dependencies as `unity-results/sg_best_lod.unitypackage`. The file size, SHA256 and included asset paths are recorded. The recursive dependency list is explicitly filtered to `Assets/`: Unity's default `IncludeDependencies` would also copy URP registry package source files. This package requires a URP project (the validation version is URP 17.3.0); it does not contain pipeline source files, the Unity Library cache or install URP itself. Its original high mesh's two tiny-area-face diagnostic remains recorded, and reduced levels retain visible artifacts in the generated shape.

Four orthographic 512×512 PNGs (front, three-quarter, side, rear) use one fixed URP light and flat ambient lighting. The camera framing fits each case's bounds. The test checks nonbackground pixels and magenta fallback pixels. A successful render shows the imported material can draw in this editor configuration. It does not establish geometric fidelity, consistent unseen geometry, shader correctness on other hardware, perceptual quality, or gameplay frame time. Render timings are one-off editor diagnostics with shader warm-up and are unsuitable as benchmarks.

The render uses the documented [URP render request API](https://docs.unity.com/en-us/engine/6000.0/manual/cameras/urp/multiple/user-render-requests). Unity runs with `-batchmode -force-d3d11`, with a graphics device initialized. As documented in [Unity editor command line arguments](https://docs.unity.com/en-us/engine/6000.7/manual/unity-editor/command-line-arguments/editor), `-nographics` skips graphics-device initialization and is not suitable for this render test.

Run after packages are complete:

```powershell
& './docs/research/2026-10-11-modelagem-3d/run_unity_validation.ps1'
```

Or pass `-CaseNames @('case_a','case_b')`. Packages are copied from `data/research-2026-10-11/exports/<case>/Forge3D_Asset` into the disposable project. Results are written under `data/research-2026-10-11/unity-results`; `unity-validation.json` is the aggregate report and individual JSON/PNG files retain each case's measurements.

The identical combined summary is also written to `data/research-2026-10-11/unity-validation.json` for the research publisher. It includes separate `originalControlFailedAsExpected`, `allGeneratedImportCompatibilityPassed`, `allGeneratedSurfaceCleanlinessPassed`, `generatedPackageCount` and `successfulPackageImports` fields.

The aggregate `passed` remains false and the command returns 1 when the original fixture is included, because it intentionally retains a confirmed triangle-fidelity failure. The high SG mesh also fails the stricter surface-cleanliness gate due to two near-zero-area faces despite passing import compatibility (both have nonzero area). Inspect individual case fields to distinguish these diagnostics from package import, material, prefab and LOD setup results. Unity exit 2 means the validator itself could not finish; script compile errors are recorded in the Unity log.

In this environment the initial sandbox launch reached the license client but failed hardware queries with `UnauthorizedAccessException`. Unity licensing/graphics execution may need the normal approved unsandboxed tool launch. No license, account, credentials, or paid service is created by the validator.

## Final observed results

Final batch completed at 2026-10-11 19:31:08 UTC on Unity 6000.3.0f1 with an NVIDIA GeForce RTX 4060. `unity-combined-final.log` records the complete run. All six generated packages passed import compatibility, original importer, expected triangle/dimension checks, finite UV/normal/tangent checks, URP Lit material checks, prefab serialization, bounds proxy checks and four editor renders each. All eight cases produced four 512px renders, plus three forced-LOD renders (35 PNGs total).

| Case | Imported triangles | Unity vertices | Albedo size | Import compatible | Faces at/below area tolerance | Exact zero-area faces |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| Original procedural control | 714 (Blender 1,092) | 1,213 | None | No | 235 | 120 |
| Clean procedural control | 214 | 251 | None | Yes | 0 | 0 |
| SG high | 319,266 | 179,037 | None | Yes | 2 | 0 |
| SG medium | 31,926 | 22,986 | None | Yes | 0 | 0 |
| SG low | 6,384 | 5,961 | None | Yes | 0 | 0 |
| SR neural texture | 96,468 | 53,856 | 1024×1024 sRGB | Yes | 3 | 0 |
| SR vertex bake | 96,468 | 53,856 | 512×512 sRGB | Yes | 3 | 0 |
| SR vertex bake 1024 control | 96,468 | 53,856 | 1024×1024 sRGB | Yes | 3 | 0 |

The combined summary reports `successfulPackageImports=6`, `allGeneratedImportCompatibilityPassed=true`, `originalControlFailedAsExpected=true`, and `allGeneratedSurfaceCleanlinessPassed=false`. Strict aggregate `passed=false` and Unity exit 1 reflect those retained diagnostics; there is no validator exception or C# compile failure in this final batch.

The SG LOD setup passes with saved/reloaded levels 319,266 → 31,926 → 6,384, correct proxy bounds/raycast and three valid forced-level renders. Archive inspection verifies that its exported package contains one prefab, three original FBX payloads and three materials, all referenced prefab asset GUIDs, and no URP source or Library cache. Each FBX payload's SHA256 matches the corresponding import report. `sg_best_lod-package-inspection.json` records the final package identity.

Visual inspection of the SR three-quarter renders shows clear holes and poor reconstructed chair depth/leg/back geometry even though the technical render checks pass. The three SR textures look similar in this view. That observation is specific to this controlled chair and view; the test does not measure general perceptual quality or prove that a larger texture adds detail. The SG renders also retain visible generated-shape artifacts, and low LOD smoothing/faceting changes remain visible.
