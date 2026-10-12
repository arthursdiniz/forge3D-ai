# Major Quality / Character Intelligence — implementation plan
> Executar inline com superpowers:executing-plans, testesRED→GREEN e uma revisão independente final.
**Goal:** ampliar arquitetura atual com fluxoCharacter/Quality/Geometry/GameReadylocal e provas reais naRTX4060.
**Architecture:** preservarAPI/Store/Worker; módulos separados, subprocessos/envs isolados, versões imutáveis. Contratos e fluxo UI consumindo recursos comprovados.
**TechStack:** Python3.12/PyTorch2.5.1CUDA12.4,FastAPI/Pydantic2/SQLite,MediaPipeCPU/Trimesh/SciPy/Pymeshlab,Blender4.5.3,React19/Three,Unity6000.3.
**Spec:** ../specs/2026-10-12-major-quality-design.md
**GlobalConstraints:** originais preservados; nenhumproprietary/gated/pago; single-image não éMV; geometriaantescor; semsmoothing/remeshautomático; labelsincerteza;1heavyjob; licença/testepessoal; nada de métricas arbitrárias.
**ReviewFocus:** uploadvistas/coords inválidos;poseanimesemdetecção ecorreçãomanual;assimetriaintencional/pose dinâmica;cancelamentoN/latecommit;UVs/normalmap/exportsuntextured/stale metadata.

### Task1 — Contratos, preservação, configuração/GPU
Files:new backend/config.py,gpu_manager.py,progress.py,provider_contracts.py;modifyproviders/app/schemas/storage/worker;teststest_major_contracts/test_gpu_manager/test_progress.
- [x] RED:olddefaults;QualityMode1/3/5+unsupportedTS seeds;Natomiccancel;typedOOM;Blenderpath;invalidviews/landmarks.
- [x] Snapshot/newQArootdata/major-quality-20261012;GREEN validatedcontracts/runtimepreflight/atomicJSON/progresstiming.
- [x] Test task/fullrelevant;recordruling/progress.

### Task2 — CharacterUnderstanding e referências
Files:new backend/character_understanding.py,character_analysis_runtime.py,character_routes.py;setup/downloadscripts,new.venv-character;testscharacter_understanding/routes.
Interface:analysis JSON {id,source_hash,category,pose,landmarks,regions,proportions,warnings,method,uncertainty};manual corrections validated beforegeneration.
- [x] RED confidence filtering/ratios/noinventedregion/dynamicpose/manuallandmarks;GREEN CPUposeengine/offline/source+overlay/update persistence.
- [x] Instalar CPUdep isolada/downloadposepúblico comhash/card/licença;medirHinata/clayactual.

### Task3 — GeometryIntegrity/CharacterQualityAnalyzer
Files:newbackend/geometry_integrity.py,character_quality.py,quality_report_cli.py;testsmetrics.
Interface:inspect scene→measuredQC;reportcharacter→perviewIoU/ratios/availableNOTMEASURABLE;beforeafterandwarnings.
- [x] RED duplicatedtriangles/inconsistentwinding/openintentional/components/poseconf;GREEN algorithms/selectivechecks/notfakeanatomy.
- [x] ActualHFmodels outputs diagnostics/render/metadata; nochangesoriginal.

### Task4 — Symmetry e sculpt seletivos
Files:newbackend/symmetry_correction.py,sculpt_refinement.py;modifyrefine_mesh/schema/worker;testssymmetry/sculpt/API.
- [x] RED plane offset/yaw,mutualcorrespondences,boundedmovement,UVs/protectedROI/asymmetricpose/refusals;GREEN versions/refinement+rollback.
- [x] RealHinata/ownreferencecases macrovssoftsymmetryvsprotectedasymmetryclay5views. Onlyclaimmeasuredimprovements.

### Task5 — BaseMesh experimental e fixtures próprios
Files:newbackend/character_base_mesh.py;blender/create_character_fixtures.py;testsbase_mesh;benchmarkscript7cases.
- [x] RED manualanatomiclandmarksrequired/proportions/volume/licenselabel;GREEN proceduralbodytemplateassisted; keepgenerativealternative.
- [x] Generate7ownedfixtureimages+GT5views/landmarks+semanticregions,safeintendedparts;neverclaimtheseasAIoutputs.

### Task6 — N candidatos eQualityMode + multi references
Files:character_advanced.py,inference_hy.py,inference_sg.py,worker.py/storage.py,reference_atlas.py/reference_texture.py,qualityschemas.
- [x] RED seedsN/wrap/cancellation/sharedload/defaultlegacy2/multiviewvalidity;GREEN batchNwithraw/latents/clay/sourcebundle/reports/atomicpublish.
- [x] Front-onlygenerators ignoreextraimageconditioning explicitly,compareadditionalviews/projectvisiblefront/back/sides optionalwithzbuffer/perviewmaskcoverage;textureunknownneutral.
- [x] Actual3Hinata and5economicfixturecandidates,bodydiagnostic;measuretotal/Torch/perstage.

### Task7 — Novosprovedores e setup honesto
Files:newbackend/hunyuan_mv_provider.py/inference_mv.py/spar3d_provider.py/inference_spar3d.py;scriptsdownloadmv/setupSPAR;persistentcapabilityproofs.
- [x] ValidateofficialconfigAPI/licences/hashes;MV4.93GB public,pinnedsamecode/offlinereal;min2compatibleviews;tryCUDA/offloadonlyrequiredvalidated.
- [x] SPARauth/compiler missing remainblocked;implementadapter/setupgates/lowVRAMflag/status,inference-not-tested,neveravailablefake.
- [x] TRELLIS2 descriptor with official Linux/24GB requirement; Hunyuan2.1 deferred and not claimed compatible.

### Task8 — GameReady, materiais eexports
Files:newblender/game_ready.py,backend/materials.py;modifyblenderpipeline/worker/schemas/unityImporter;testsnormal_bake/export.
- [x] RED targetbudget,preservinghighpoly;Baking1K/2K/4K/normal maptangent/nonflatfixture/UV/integrity/alpha;GREEN CPUBlenderselectedhigh→lowwithboundedcage+actualmaps,atlaspreserved,GLB/FBX/OBJ+manifestallfiles.
- [x] UnitynormalmapTextureType.NormalMap/keywords/Lit+Standard,testbothgeometry-only/texturedhighlow1.5m/prefab/normals.

### Task9 — Interfaceintegrada
Files:newfrontend/src/CharacterPanel.tsx,QualityPanel.tsx,ModelSetupPanel.tsx;modifyApp/api/Viewer/styles.
- [x] CharacterMode/manualcategorypose/pointdrag/regionsbeforegenerate/multiviewuploads,Quality1/3/5,candidateclaycomparisons/diagnostics,simmetry/refinementoffdefault,baseexperimentalstrategy.
- [x] HighPoly/GameReadytargetnormalbakeresolution,exports/setupBlender/GPUpresets/stageelapsed/timing/errors. Preserveold UItechnology/colors,donotredesigncosmetic.
- [x] Build/typechecks,Playwrightactualflowsdesktop/mobile/download/latefail/cancel.

### Task10 — Prova final/documentação/revisão
- [x] Fulltests/representativebenchmarks7ownedcases+Hinata+object;single/MV nativewhenavailable;all7fixtures in5viewclay; Hinata5viewclay/textured; hashes/licences/timesGPUreal.
- [x] UnityrealGameReady/normalbake;browser→API→GPU/CPU→GLB→FBX→Unity tested.
- [x] Freshreviewonceperexecuting-plans, fiximportantRED→GREEN/fullsuite.
- [x] README/install/modeldoc/QA/progress/newreportmanifestfiles+acceptancematrixcomplete/partial/blocked. No equivalenceMeshy/anatomy/rig false.

# Ledger
Task0 audit complete:122files/HW/docs verified; existing71test evidencepreserved. Newrequestexplicitlyauthorizesallviableimplementation/downloads; no redundantapprovalgates.
Preflight sharedinterfaces:schemas↔app/worker/frontend;analysis↔CharacterQuality/BaseMesh;Nbatch↔Storeatomic;GameReady↔manifest/UnityImporter;MVproof↔provideravailability. EachhasREDcontracttests above.

Task1 contracts/GPU/progress core RED→GREEN9tests. Baseline124files/19assetdirs/SQLitebackup preserved before code changes. Task2 CPU detector installed separately/mediaPipe0.10.32;Hinata actual33landmarks/0.832s,overlay visually inspected. Confidence/ratios/manual/no-fake/analsyssourcebinding6tests pass. Task2 routes integrated, UI pending. MV4.93GB/publicpin/hash andpose5.78MB downloaded and verified.
Ruling: ownprocedural7referencefixture generator staged early because nativeMV requires legitimate actualfront/side/back input; no such usermultiviewbundle provided. Fixtures explicitlylabellednonAI/CC0; never substitute theirgroundtruth mesh for AIoutputs.

Task3 integrity+proportion/silhouettecore6testsRED→GREEN; measuredper-shellorientation/duplicates/winding/openpolicies implemented,optional actualMeshLabintersection+64inwardrays inisolated.venv-geometry. NativeMVactual3views/50steps/256 passed155.67s/5558.2MiBallocated/6194reserved;144728tri/closed/outward1component/nooffload. Sevenownedfixtures generated35RGBAviews+GT/projections/CC0; nofakeAIlabels. MVrender/export/productintegration pending.

Task4 purealgorithms:SymmetryCorrection3testsRED→GREEN(localplane,mutualNN,bounds/protected/dynamicrefusal);SculptRefinement2testsRED→GREEN(micro,sharp/boundaryprotection). NotwiredUI/worker yet. RuntimeHQdiagnostic oflegacyHinata executingseparategeometryenv;MCNativeMVavailableexperimentonly,need5view/FBXproof.

Task6 sequential shared-load Hunyuan-mini/TripoSG/HunyuanMV QualityMode1/3/5 generalized; legacy2 preserved. Publication12testsRED→GREEN and MV/API/referencehash/cancellation19tests pass. NativeMV adapter3realviews seed42 reproduced144728tri/5558.2MiB,157.18s; rendering/FBX in progress. GeometryOperations4testsRED→GREEN selectivebounds/neutralpose/UV/volume guards. WorkerGPUManager14testsRED→GREEN preflight/timeline/preservation; diagnostics CPU wired, integration validation pending.

Task6 actualHinata3raws seeds42/43/44; sharedload30.93s+27–28s/candidate, geometry-only preprocessing finished after same-file Windowscopybug. BugRED→GREENtest and preservedrawcopy in hinata-quality-three-preserved; active inference+processing151.39s (interruptionexcluded),4182.2MiB peak. ActualSG5animefixture complete, timingspendingread. Task8 actualCPUhigh→low normal fixture12096→2000/normalvariance.02958 passed; actualHinata115506→20000/2Kactualnormal passed5.62s; FBX+GLB+OBJ created, Unitypending. Task9 Character/Quality/Setup UIbuildpassed; CharacterTools integrated compile+browserpending. Fullsuite108passed before latesttexture/bake additions.
Ruling: Blender stats are Z-up in its internal scene, but exportedGLBs retain canonicalY-up. ActualTrimeshcoordinates measured; CPUdiagnostics/operations use Y-up, avoiding axisregression.

Pre-finalverification118tests passed; actualUIHinata3 completed159.406s/Torch4182.2MiB/NVIDIApeak5665MiB/67samples. Child44=4d0fd422ce9445aa804ebbc222425d10; GameReadyc8606699b56d4aad81fdedbe69970029→export8fe8143c258f48cab8236265c5bf2061, downloadsFBX/GLB/OBJ/ZIP200. Actualcancel2dfb995277fb461c8b5dd436c5bb8836 stayedcancelled/nochildren. Native2/3/4realrenderFBX proofs passed; native3faces/vertices/latents exactrepro. SevenactualNNcases+13selectivecorrections passed; dynamicSymmetryrefused. Native4lateralIoU.648→.867,front.921→.900. UnityURP/Standardnormal2K/prefab andgeometry-only passed outside sandbox. NoMeshy/face/rig/learnedanatomy claim.
Ruling: Meso/face/finger reconstruction and fullanatomy cannot be honestly supplied from singleview with current8GBmodels. Delivermeasuredcontrols/template/MV/baking and explicitlymarkthoseintelligencegoals partial; practicalnextstep actualmatchingfront/side/backplusmanualretopology. Cost: userstillneedsreferences/artistwork for identity/rig.


Final delivery ledger (12Oct): all viable tasks implemented/verified, with scope limits in docs/MAJOR_QUALITY_20261012.md. Full136tests10.76s/buildpassed. EightImportantreviewfindings fixed in one pass, noCritical. New finalQAcaughtUV-seam decimation failure; exact boundary-pair topology restoration onLOW plus preservation ofsmall shells yields20K/14components/0boundary/nonmanifold/intersection and0.1002%volumechange. RealWorkerGameReadyguard rejects regressions, noholefill. Timingfix RED→GREEN + actual8.797sworker/10.058spollproof. FinalURP/Standard4Kcolor+normal20Kimport/prefabpassed inUnityFinalSafe4KValidation. CroppedopaqueTripoSRnormal-mode andlaterprojection passed. Finalpreservation205files/19assets/HinataSHApassed. BrowserdelayedSave/toggles/seeds/numericcoordinatepath/downloads/mobilepassed. NativeMV2/3/4andsevenactualNNfixtures/preserved5viewbeforeafterproofs done.
Rulings: learnedanatomy/face/fingers/semanticclothing segmentation, animationquadretopo/rig, Meshyparity, arbitrarysingle-imagehiddenidentity remainpartial/unavailable. SPARweights/runtimeblocked; no gated/paid/auth/driverinstall. Hunyuan2.1deferred. OldunsafeGameReadybakeQAversionsarehistorical, neverreusedasfinalproof. NoGitmetadata:keepcurrentlocalworkspaceandallsource/assetQA snapshots, noPR/merge/deletion. Reviewbudgetonefreshreviewcompleted; nosecondreviewrequested.
