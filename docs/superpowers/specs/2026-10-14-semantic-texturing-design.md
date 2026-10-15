# Semantic Character Intelligence / Reference Fidelity

Authoritative request: attachment117396a5-85dc-4be9-aa5c-d0b13bf67f78/Texto colado.txt. Architectural change, implemented continuously inline as expressly requested: “Execute as etapas de forma contínua” and “sem parar após o planejamento”. These instructions override routine skill spec/plan approval pauses and generic Git commit/cleanup steps. Preserve current dirty checkout and every original asset; snapshot before implementation, do not stage/reset/push/merge.

Goal: real local semantic masks must constrain texture projection/composition and localized editing, with immutable versions, original geometry/channels and reproducible evidence. This is not universal character reconstruction or a new PBR model.

## Provider and scope

Research all nine named official projects before related implementation. AnimeSeg Mask2Former/DINOv2 code and weights lack an explicit license in inspected official tree/card/setup; no download. StyleAnime inspected tree exposes only README, no released runnable parser. SCHP code MIT, separate pretrained/dataset provenance/license and native compiled normalization need further verification; do not install on that basis. Reuse pinned Anime-Face-Segmentation seven-class UNet/MobileNet already executed in backend/hair: background/hair/eyes/mouth/face/skin/clothes. It is a portrait model; crop is explicit, output outside crop is unknown, transparent background can be observed background. No invented shirt/shorts/brow classes. Manual raster edits may use the broader taxonomy. Realistic profile starts manual; stylized anime inference is labeled as experimental portrait segmentation.

Separate segmentation response from calibrated confidence; probabilities are uncalibrated. Store native and common labels, per-class masks/overlay, source hashes/dimensions, inference time/memory, code/checkpoint revision/license, manual-edit origin and color/pattern descriptors. Reuse existing face detector/Character Intelligence only as suggestions bound to the same image hash; pose bounds never become neural semantic labels.

## Data and projection

Optional semantic_analysis serial jobs have no model asset. Input is a completed mesh and front/back/left/right real images, with per-view reviewed source/target boxes, paired landmarks, portrait crops and manual source/target strokes. RegionCamera provides actual world position, normals, UV, owner and primitive/depth visibility. Source labels sample nearest; observed RGB samples original pixels. Each view requires compatible pose/alignment review before painting. Unknown remains unknown; hidden geometry is not assigned from frontal rectangles.

Analyses persist versioned labels and manual origin, target renders, semantic UV maps and projected source/target ownership. Source/target disagreement blocks transfer between incompatible classes; face/skin may match within an anatomical family, eyes/mouth/hair/clothes remain distinct. Unknown target may be accepted only by an explicit reviewed policy, labeled projected/estimated rather than independent semantic proof. Manual classes override learned labels. Expose projected labels, coverage, conflicts, provenance and per-face summaries; surface picking samples matching node/UV maps.

## Texture behavior

Reference Fidelity is a new optional provider in existing independent texture engine. It preserves existing UVs, alpha, normals and non-albedo data maps; no mesh processing, arbitrary UV rebake or global smoothing. Sources without valid albedo/UVs first use existing global texturing. Selection by actual semantic classes affects allowed texels. Preserve protected classes/materials/polygons and all pixels outside edit masks exactly. Fuse multiple real observations only within compatible semantic classes; edges/patterns choose best visible observation instead of averaging. Preserve numbers/symbols as pixels, no OCR reconstruction.

Optional completion reuses current MV-Adapter SDXL via existing generate_views, explicit previously authorized licenses, serial GPU and validated offload. Observed pixels take priority; generated pixels fill eligible unobserved texels only, never protected ones. Generated facial categories on surfaces without observed facial evidence are rejected; semantic predictions on synthesis remain estimates. No unsupported spatial mask conditioning is claimed. Reference/region color adjustment and masked composition controls must cause real changes. Existing providers remain accessible.

UV seam correction uses existing 3D duplicated-position/normal adjacency plus same semantic class and edit mask. Conservative surface fill uses only same-class, same-material adjacent surface samples at bounded distance; no atlas-neighbor flood or fake neural inpainting. Record filled texels as propagated/estimated. Illumination is not physically disentangled; diagnose dark/highlight fractions without claiming removal.

## Interface and safety

Lazy SemanticWorkspace inside Texturização IA; original/reference/render overlays, class selection, normalized brush/eraser/polygon edits and restore learned labels. Save corrections into new analysis versions, not mutate previous reports. Source and target editing use intrinsic pixel coordinates under display scale. Binding source/axis/image changes invalidates analysis and cancels stale asynchronous state. Surface picking shows known/unknown class and evidence; selected class scopes operations. Approval/rejection selects versions, does not overwrite. Analysis jobs cannot become fallback mesh/library sources.

Pydantic finite/size/class checks; images≤20MB/25Mpx, strokes≤2048points/256strokes, normalized coordinates, texture≤4096. Use isolated existing .venv-hair for semantic runtime with existing package paths; core API imports no NumPy/Torch. Hash/source/axis/analysis checks before queue and again in subprocess. Cancelled jobs cannot publish. No network in inference, gated/paid services or core runtime/driver changes.

## Validation

Snapshot current source/dirtyGit/assets and current229-test baseline. Real caseA Kageyama/Naruto anime hair; B Hinata uniform; C existing Naruto 3D stylized reference (not a photoreal human benchmark). Compare same source/pose/config and prior texture before/after front/sides/back, unlit/clay. Manual independent masks clearly annotated by author may measure per-class IoU; predicted masks do not become ground truth. Report cross-class blocked/accepted transfer, exact protected pixels, observed/generated/propagated coverage, RGB/SSIM in visible aligned regions, seam differences, world geometry and channels, time and sampled/PyTorch VRAM separately.

Run real segmentation→projection→paint→UV→GLB/FBX/OBJ→Unity URP/Built-in; real neural completion and equivalent baseline when resources permit. SD2.1 official base currently401, document unavailable comparison, no mirror workaround. Full tests/build/browser, missing weights/manual errors/cancel/retry/old assets. One fresh final reviewer per executing-plans; one Important/Critical RED→GREEN fix pass, no re-review. Deliver measured gains and limits without universal fidelity claims.
