# coding=utf-8
# Copyright 2025 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: skip-file
"""Utility functions for handling configurations."""

from collections.abc import Mapping, Sequence
import dataclasses
import enum
import functools
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from absl import flags
from flax.core import FrozenDict
import gin
from google_research.yobo.internal import math
import jax
import jax.numpy as jnp
import optax

BboxType = tuple[tuple[float, float, float], tuple[float, float, float]]


gin.add_config_file_search_path('experimental/buff/battal/mipnerf360/')

configurables = {
    'math': [math.power_ladder, math.create_learning_rate_decay],
    'jnp': [
        jnp.reciprocal,
        jnp.log,
        jnp.log1p,
        jnp.exp,
        jnp.sqrt,
        jnp.square,
        jnp.sum,
        jnp.mean,
        jnp.abs,
    ],
    'jax.nn': [jax.nn.relu, jax.nn.softplus, jax.nn.silu, jax.nn.sigmoid],
    'jax.nn.initializers.he_normal': [jax.nn.initializers.he_normal()],
    'jax.nn.initializers.he_uniform': [jax.nn.initializers.he_uniform()],
    'jax.nn.initializers.glorot_normal': [jax.nn.initializers.glorot_normal()],
    'jax.nn.initializers.glorot_uniform': [
        jax.nn.initializers.glorot_uniform()
    ],
    'optax': [
        optax.adam,
        optax.sgd,
        optax.adamw,
        optax.warmup_exponential_decay_schedule,
        optax.warmup_cosine_decay_schedule,
        optax.linear_schedule,
        optax.constant_schedule,
        optax.polynomial_schedule,
        optax.join_schedules,
        optax.piecewise_constant_schedule,
        optax.piecewise_interpolate_schedule,
    ],
    'camera_delta': camera_delta.CAMERA_DELTA_CLASSES,
}

for module, configurables in configurables.items():
  for configurable in configurables:
    gin.config.external_configurable(configurable, module=module)


# CallDef is a construct that makes it easier to use callables with arguments
# in Gin configs. A CallDef is simply a tuple containing a callable and keyword
# arguments the callable should be called with.
#
# See: `parse_call_def` and `parse_call_def_partial`.
#
# Example:
#   ```
#   >> def add(a, b):
#   >>   return a + b
#
#   >> call_def = (add, {'a': 1, 'b': 2})
#   >> config_utils.parse_call_def(call_def)
#   3
#   ```
CallDef = tuple[Callable[Ellipsis, Any], Mapping[str, Any]]


def parse_call_def(call_def):
  """Parses a function call definition.

  Args:
    call_def: A tuple containing (fn, kwargs).

  Returns:
    The result of `fn(**kwargs)`.
  """
  fn, kwargs = call_def
  return fn(**kwargs)


def parse_call_def_partial(call_def):
  """Parses a function call definition partially.

  Parses a CallDef, but instead of evaluating the function immediately,
  return a partial function with the given kwargs.

  Args:
    call_def: A tuple containing (fn, kwargs).

  Returns:
    A partial function `fn(**kwargs)`.
  """
  fn, kwargs = call_def
  return functools.partial(fn, **kwargs)


@gin.configurable
def join_schedule_defs(
    schedule_defs, boundaries
):
  """A gin configurable wrapper around `optax.join_schedules`."""
  schedules = [parse_call_def(s) for s in schedule_defs]
  return optax.join_schedules(schedules, boundaries)


@gin.constants_from_enum
class MaskInput(enum.Enum):
  """Specify the format of mask.

  Attributes:
    NONE: No mask used
    PNG: Masks are `.png` images inside a `masks/` subfolder
    PROTO: Masks are `.proto`
      `geo_machine_perception.semantic_index.SemanticIndexDataEntry`
  """

  NONE = enum.auto()
  PNG = enum.auto()
  PROTO = enum.auto()

  def __bool__(self):
    # `if config.use_mask:` is `False` when `NONE`
    return self is not MaskInput.NONE


@gin.constants_from_enum
class ModelType(enum.Enum):
  DEFAULT = enum.auto()
  DEFERRED = enum.auto()
  MATERIAL = enum.auto()


@gin.configurable()
@dataclasses.dataclass
class Config:
  """Configuration flags for everything."""

  debug_mode: bool = False  # If True, compute some expensive debug outputs.
  dataset_loader: str = 'llff'  # The type of dataset loader to use.
  batching: str = 'all_images'  # Batch composition, [single_image, all_images].
  batch_size: int = 16384  # The number of rays/pixels in each batch.
  patch_size: int = 1  # Resolution of patches sampled for training batches.
  factor: int = 0  # The downsample factor of images, 0 for no downsampling.
  # Integer downsampling factors to use for multiscale training.
  # Note 1 is included by default! Use [2, 4, 8] for mip-NeRF 2021 convention.
  multiscale_train_factors: Optional[List[int]] = None
  # Load images in COLMAP vs alphabetical ordering (affects heldout test set).
  load_alphabetical: bool = True
  forward_facing: bool = False  # Set to True for forward-facing LLFF captures.
  # Function for transforming loaded poses in non-forward-facing scenes.
  transform_poses_fn: Optional[Callable[Ellipsis, Any]] = None
  # If True, training cameras will be set to the identity.
  use_identity_cameras: bool = False
  use_perturbed_cameras: bool = False
  camera_perturb_sigma_look_at: float = 0.0
  camera_perturb_sigma_position: float = 0.0
  camera_perturb_sigma_dolly_z: float = 0.0
  camera_perturb_sigma_focal_length: float = 0.0
  camera_perturb_intrinsic_single: bool = True
  camera_perturb_zero_distortion: bool = False
  camera_perturb_dolly_use_average: bool = False
  use_mesh_face_normals: bool = False
  meshfile: str | None = None
  ckpt_dir: str | None = None

  render_path: bool = False  # If True, render a path. Used only by LLFF.
  llffhold: int = 8  # Use every Nth image for the test set. Used only by LLFF.
  # If true, use all input images for training.
  llff_load_from_poses_bounds: bool = False  # If True, load camera poses of
  # LLFF data from poses_bounds.npy.
  llff_use_all_images_for_training: bool = False
  load_ngp_format_poses: bool = False  # Use `transforms.json` file for poses.
  # Use `metadata.json` for new ARCore poses, `original_metadata.json` for old.
  arcore_format_pose_file: Optional[str] = None
  colmap_subdir: Optional[str] = None  # Where to find COLMAP pose data.
  image_subdir: Optional[str] = None  # Where to find image data.
  load_colmap_points: bool = False
  use_tiffs: bool = False  # If True, use 32-bit TIFFs. Used only by Blender.
  use_exrs: bool = False  # If True, use EXR files.
  compute_disp_metrics: bool = False  # If True, load and compute disparity MSE.
  compute_normal_metrics: bool = False  # If True, load and compute normal MAE.
  gc_every: int = 10000  # The number of steps between garbage collections.
  disable_multiscale_loss: bool = False  # If True, disable multiscale loss.
  # If not `NONE`, loads image masks from 'masks' directory.
  use_masks: MaskInput = MaskInput.NONE
  mask_threshold: float = 0.0
  dtu_light_cond: int = 3  # Which DTU dataset lighting condition to load.

  randomized: bool = True  # Use randomized stratified sampling.
  near: float = 2.0  # Near plane distance.
  far: float = 6.0  # Far plane distance.
  scene_bbox: None | float | BboxType = None
  # Near and far plane distance in meters. If not None, calibration images are
  # used for conversion to scene units.
  near_plane_meters: Optional[float] = None
  far_plane_meters: Optional[float] = None
  model_type: ModelType = ModelType.DEFAULT  # Model type to use
  linear_to_srgb: bool = False  # Convert linear radiance to sRGB
  checkpoint_dir: Optional[str] = None  # Where to log checkpoints.
  render_dir: Optional[str] = None  # Output rendering directory.
  data_dir: Optional[str] = None  # Input data directory.
  vocab_tree_path: Optional[str] = None  # Path to vocab tree for COLMAP.
  render_chunk_size: int = 16384  # Chunk size for whole-image renderings.
  num_showcase_images: int = 5  # The number of test-set images to showcase.
  deterministic_showcase: bool = True  # If True, showcase the same images.
  vis_num_rays: int = 16  # The number of rays to visualize.
  # Decimate images for tensorboard (ie, x[::d, ::d]) to conserve memory usage.
  vis_decimate: int = 0

  # Flags for performing semantic consensus similar to Semantic-NeRF and
  # Distilled Feature Fields (DFFs). Aside from color and density, the model
  # also predicts an arbitrary size semantic feature for each pixel.
  # If semantic_dir is provided, an additional Semantic MLP will be used to make
  # such prediction. For each input image, we should have a corresponding file
  # under semantic_dir. The file should have the same file name, and dimensions
  # of [H, W, C].
  semantic_dir: Optional[str] = None  # Input directory of semantic data.
  semantic_format: Optional[str] = None  # Semantic format ('npy' or 'image').

  # Only used by train.py:
  max_steps: int = 250000  # The number of optimization steps.
  early_exit_steps: Optional[int] = None  # Early stopping, for debugging.
  visualize_every: int = 25000  # How many steps between model visualizations.
  checkpoint_every: int = 25000  # The number of steps between checkpoint saves.
  checkpoint_keep: int = 2  # Keep the last N checkpoints saved to disk.
  print_every: int = 100  # The number of steps between reports to tensorboard.
  print_camera_every: int = 500  # The number of steps between camera reports.
  train_render_every: int = 5000  # Steps between test set renders when training
  jax_rng_seed: int = 20200823  # The seed that JAX's RNG uses.
  np_rng_seed: int = 20201473  # The seed that Numpy's RNG uses.
  disable_pmap_and_jit: bool = False  # If True disable the training pmap.
  cast_rays_in_train_step: bool = False  # If True, compute rays in train step.
  cast_rays_in_eval_step: bool = False  # If True, compute rays in eval step.
  jitter_rays: int = 0  # If True, compute rays in train step.
  data_loss_type: str = 'charb'  # What kind of loss to use ('mse' or 'charb').
  charb_padding: float = 0.001  # The padding used for Charbonnier loss.
  data_loss_mult: float = 1.0  # Mult for the finest data term in the loss.
  data_coarse_loss_mult: float = 0.0  # Multiplier for the coarser data terms.
  semantic_loss_mult: float = 1.0  # Mult for the loss on the semantic MLP.
  semantic_coarse_loss_mult: float = 0.0  # Mult for the coarser semantic terms.
  # Multiplier(s) for the interlevel loss that supervises the proposal MLP(s).
  # Setting value to 0 indicates no semantic head in proposal MLP(s).
  interlevel_loss_mults: Union[float, Tuple[float, Ellipsis]] = 1.0
  use_spline_interlevel_loss: bool = False  # Enable a spline-based loss.
  use_normal_weight_ease: bool = False
  normal_weight_ease_frac: float = 0.0
  use_normal_weight_decay: bool = False  # Enable normal weight decay
  normal_weight_decay_start_frac: float = 0.2
  normal_weight_decay_rate: float = 0.8
  # How much to blur in the spline-based loss.
  interlevel_loss_blurs: Tuple[float, Ellipsis] = (0.01, 0.001)

  orientation_loss_mult: float = 0.0  # Multiplier on the orientation loss.
  orientation_coarse_loss_mult: float = 0.0  # Coarser orientation loss weights.
  # What that loss is imposed on, options are 'normals' or 'normals_pred'.
  orientation_loss_target: str = 'normals_pred'

  predicted_normal_loss_mult: float = 0.0  # Mult. on the predicted normal loss.
  predicted_normal_reverse_loss_mult: float = (
      0.0  # Mult. on the predicted normal loss.
  )
  # Mult. on the coarser predicted normal loss.
  predicted_normal_coarse_loss_mult: float = 0.0

  param_regularizers: FrozenDict[str, Any] = FrozenDict({})
  # An example of total L2 loss (weight decay) on the NeRF MLP and average
  # Geman-McClure loss on the first layer of the proposal MLP:
  #   param_regularizers = {
  #       'NerfMLP_0': (0.00001, @jnp.sum, 2, 1),
  #       'PropMLP_0/Dense_0': (0.01, @jnp.mean, -2, 1),
  #   }
  # Any model parameter that isn't specified gets a multiplier of 0. See the
  # train_weight_l2_* parameters in TensorBoard to know what can be regularized.
  # The hyperparameters are of the form (mult, alpha, scale) that parameterize
  # a general robust loss, see https://arxiv.org/abs/1701.03077 for details.

  eikonal_loss_mult: float = 0.0  # Multiplier on the eikonal loss.
  eikonal_coarse_loss_mult: float = 0.0  # Multiplier on the coarser eikonal.
  lr_init: float = 0.002  # The initial learning rate.
  lr_final: float = 0.00002  # The final learning rate.
  extra_opt_params: FrozenDict[str, Any] = FrozenDict({})
  extra_losses: FrozenDict[str, Any] = FrozenDict({})
  lr_delay_steps: int = 512  # The number of "warmup" learning steps.
  lr_delay_mult: float = 0.01  # How much sever the "warmup" should be.
  adam_beta1: float = 0.9  # Adam's beta2 hyperparameter.
  adam_beta2: float = 0.999  # Adam's beta2 hyperparameter.
  adam_eps: float = 1e-6  # Adam's epsilon hyperparameter.
  grad_max_norm: float = 0.001  # Gradient clipping magnitude, disabled if == 0.
  grad_max_val: float = 0.0  # Gradient clipping value, disabled if == 0.
  grad_accum_steps: int = 1  # Gradient clipping value, disabled if == 0.
  distortion_loss_target: str = 'sdist'  # The distance that distortion uses.
  distortion_loss_mult: float = 0.01  # Multiplier on the distortion loss.

  # The curve applied to distortion_loss_target before computing distortion of
  # the form (fn, **kwargs), like (@math.power_ladder, {'p':-2, 'premult':10}).
  distortion_loss_curve_fn: Optional[
      Tuple[Callable[Ellipsis, Any], Dict[str, Any]]
  ] = None
  normalize_distortion_loss: bool = False  # Makes distortion scale invariant.

  extra_loss_params: FrozenDict[str, Any] = FrozenDict({})

  cache_rgb_loss_mult: float = 0.0  # Multiplier on the distortion loss.
  residual_albedo_loss_mult: float = 1.0  # Multiplier on the distortion loss.
  emission_zero_loss_mult: float = 0.01  # Multiplier on the distortion loss.
  emission_constant_loss_mult: float = (
      0.01  # Multiplier on the distortion loss.
  )
  extra_ray_loss_mult: float = 0.0  # Multiplier on the distortion loss.
  radiometric_loss_mult: float = 0.0  # Multiplier on the distortion loss.
  light_sampling_loss_mult: float = 0.0  # Multiplier on the distortion loss.
  sample_prediction_loss_mult: float = 0.0  # Multiplier on the distortion loss.
  secondary_rgb_loss_mult: float = 1.0  # Multiplier on the distortion loss.

  num_light_samples: int = 8  # Multiplier on the distortion loss.
  num_extra_samples: int = 1  # Multiplier on the distortion loss.
  num_radiometric_samples: int = 1  # Multiplier on the distortion loss.
  num_distance_samples: int = 32  # Multiplier on the distortion loss.

  patch_loss_mult: float = 0.0  # Multiplier on patchwise depth loss.
  bilateral_strength: float = 0.0  # Strength of RGB bilateral weights on above.
  # Modulates RGB patch variance weighting of patchwise depth loss.
  patch_variance_weighting: float = 0.0

  # Only used by eval.py:
  eval_only_once: bool = True  # If True evaluate the model only once, ow loop.
  eval_save_output: bool = True  # If True save predicted images to disk.
  eval_save_ray_data: bool = False  # If True save individual ray traces.
  eval_render_interval: int = 1  # The interval between images saved to disk.
  eval_dataset_limit: int = jnp.iinfo(jnp.int32).max  # Num test images to eval.
  eval_quantize_metrics: bool = True  # If True, run metrics on 8-bit images.
  eval_crop_borders: int = 0  # Ignore c border pixels in eval (x[c:-c, c:-c]).

  # Only used by render.py
  render_video_fps: int = 60  # Framerate in frames-per-second.
  render_video_crf: int = 18  # Constant rate factor for ffmpeg video quality.
  render_path_frames: int = 120  # Number of frames in render path.
  num_dataset_images: int = -1  # Number of frames in render path.
  z_variation: float = 0.0  # How much height variation in render path.
  z_phase: float = 0.0  # Phase offset for height variation in render path.
  rad_mult_min: float = 1.0  # How close to get to the object, relative to 1.
  rad_mult_max: float = 1.0  # How far to get from the object, relative to 1.
  render_rotate_xaxis: float = 0.0  # Rotate camera around x axis.
  render_rotate_yaxis: float = 0.0  # Rotate camera around y axis.
  lock_up: bool = False  # If True, locks the up axis (good for sideways paths).
  render_dist_percentile: float = 0.5  # How much to trim from near/far planes.
  render_dist_curve_fn: Callable[Ellipsis, Any] = jnp.log  # How depth is curved.
  render_path_file: Optional[str] = None  # Numpy render pose file to load.
  render_job_id: int = 0  # Render job id.
  render_num_jobs: int = 1  # Total number of render jobs.
  render_rgb_only: bool = False  # Render spherical 360 panoramas.
  # Render resolution, as (width, height).
  render_resolution: Optional[Tuple[int, int]] = None
  render_focal: Optional[float] = None  # Render focal length.
  render_camtype: Optional[str] = None  # 'perspective', 'fisheye', or 'pano'.
  render_spherical: bool = False  # Render spherical 360 panoramas.
  render_save_async: bool = True  # Save using a separate thread.
  # Text file containing names of images to be used as spline keyframes, OR
  # directory containing those images.
  render_spline_keyframes: Optional[str] = None
  # Comma-separated list of possible values for option
  # "render_spline_keyframes". If set, the render pipeline will be executed
  # once per entry, overwriting "render_spline_keyframes" in the process.
  render_spline_keyframes_choices: Optional[str] = None
  render_spline_n_interp: int = 30  # Num. frames to interpolate per keyframe.
  render_spline_degree: int = 5  # Polynomial degree of B-spline interpolation.
  render_spline_lock_up: bool = False  # If True, no up/down tilt in path.
  # B-spline smoothing factor, 0 for exact interpolation of keyframes.
  # Interpolate per-frame exposure value from spline keyframes.
  render_spline_smoothness: float = 0.03
  # Weight associated with rotation dimensions. Higher values means preserving
  # view direction is more important than camera position. Must be >0.
  render_spline_rot_weight: float = 0.1
  render_spline_interpolate_exposure_smoothness: int = 20
  render_spline_interpolate_exposure: bool = False
  render_spline_lookahead_i: Optional[int] = None
  render_spline_fixed_up: bool = False
  render_spline_meters_per_sec: Optional[float] = None
  # If both parameters below are specified, spline keyframes that are far from
  # their neighbors will be ignored.
  render_spline_outlier_keyframe_quantile: Optional[float] = None
  render_spline_outlier_keyframe_multiplier: Optional[float] = None
  # Text file or directory with image pairs for calibrating metric scale.
  render_calibration_keyframes: Optional[str] = None
  render_calibration_distance: float = 3.0  # Default calibration is 3 meters.
  render_spline_const_speed: bool = False  # Retime spline to have const speed.
  render_spline_n_buffer: Optional[int] = None  # Extra keyframes for path.
  # A tuple of video formats to render. Accepted formats: 'mp4', 'webm', 'gif'.
  render_video_exts: Tuple[str, Ellipsis] = ('mp4',)
  # Whether or not to delete the still images after rendering a video.
  render_delete_images_when_done: bool = True
  # Whether or not videos should be rendered looped (going forwards then the
  # same way backwards)
  render_looped_videos: bool = False
  # Make videos in the main render.py binary
  render_make_videos_in_main_binary: bool = True

  # Only used by MetricHarness.
  # During training, disable LPIPS, SSIM, and shift-invariant metrics as they're
  # expensive to evaluate.
  metric_harness_train_config: FrozenDict[str, Any] = FrozenDict({
      'disable_lpips': True,
      'disable_ssim': True,
      'disable_search_invariant': True,
  })
  # During evaluation, let LPIPS and SSIM be turned on by default but still
  # disable shift-invariant metrics as they are expensive and currently unused.
  metric_harness_eval_config: FrozenDict[str, Any] = FrozenDict(
      {'disable_search_invariant': True}
  )

  # Parameters for the local color correction used in evaluating the color
  # corrected error metrics. Note that increasing any of these numbers is
  # virtually guaranteed to improve all error metrics, so these parameter should
  # be tuned by visual inspection.
  color_correction_config: FrozenDict[str, Union[int, Tuple[int, int]]] = (
      FrozenDict({
          'num_spatial_bins': [6, 10],
          'num_luma_bins': 9,
          'num_chroma_bins': 3,
      })
  )

  # Flags for raw datasets.
  rawnerf_mode: bool = False  # Load raw images and train in raw color space.
  exposure_percentile: float = 97.0  # Image percentile to expose as white.
  # During training, discard N-pixel border around each input image.
  num_border_pixels_to_mask: int = 0
  apply_bayer_mask: bool = False  # During training, apply Bayer mosaic mask.
  autoexpose_renders: bool = False  # During rendering, autoexpose each image.
  # For raw test scenes, use affine raw-space color correction.
  eval_raw_affine_cc: bool = False

  # Flags for aerial datasets.
  world_scale: float = 1.0  # Camera positions are divided by this quantity.
  z_min: Optional[float] = None  # Rays end at this Z value.
  z_max: Optional[float] = None  # Rays start at this Z value.

  # Gradient scaling
  use_gradient_scaling: bool = False  # If True, use gradient-scaling.github.io
  gradient_scaling_sigma: float = 1.0  # The gradient-scaling scale factor.

  # Loss-scaling related values
  enable_loss_scaler: bool = False
  loss_scale: float = 1000.0

  optimize_cameras: bool = False
  camera_delta_cls: Type[camera_delta.CameraDelta] = (
      camera_delta.FocalPoseCameraDelta
  )
  camera_optimizer: Callable[Ellipsis, Any] = optax.adam
  camera_optimizer_kwargs: Mapping[str, Any] = FrozenDict({})
  camera_lr_schedule_def: CallDef = (
      math.create_learning_rate_decay,
      {
          'lr_init': 1e-3,
          'lr_final': 1e-4,
          'lr_delay_steps': 2500,
          'lr_delay_mult': 1e-8,
          'max_steps': 25000,
      },
  )
  camera_lr_fn: Callable[Ellipsis, Any] = optax.warmup_cosine_decay_schedule
  camera_lr_fn_kwargs: Mapping[str, Any] = FrozenDict({
      'init_value': 0.0,
      'peak_value': 1e-4,
      'warmup_steps': 200,
      'decay_steps': 5800,
      'end_value': 1e-4,
  })

  exposure_prediction_loss_mult: float = 0.0  # Loss weight for ExposureMLP
  # Weight of the following loss (penalizes for too small or too large
  # exposures):
  # 0.5 * ReLU(min_dataset_exposure - exposure)**2 +
  # 0.5 * ReLU(exposure - max_dataset_exposure)**2
  # Not used when exposure_prediction_loss_mult = 0
  exposure_prediction_bounds_loss_mult: float = 0.1

  # If True, use coarse-to-fine which will be applied to the grid optimizer as
  # an additional scale to the learning rate.
  enable_grid_c2f: bool = False
  # The grid size containing the whole -2 to 2 volume, including the contracted
  # area.
  # coarse to fine weights.
  grid_c2f_resolution_schedule_def: CallDef = (
      optax.linear_schedule,
      {
          'init_value': 1024,
          'end_value': 8192,
          'transition_steps': 2500,
          'transition_begin': 0,
      },
  )
  grid_c2f_weight_method: str = 'cosine_sequential'

  focal_length_var_loss_mult: float = 0.0
  principal_point_var_loss_mult: float = 0.0
  principal_point_reg_loss_mult: float = 0.0
  radial_distortion_var_loss_mult: float = 0.0

  # Flags for test time camera alignment.
  optimize_test_cameras: bool = False
  optimize_test_cameras_for_n_steps: int = 200  # Gradient descent iterations.
  optimize_test_cameras_lr: float = 0.001
  optimize_test_cameras_batch_size: int = 10000
  test_camera_delta_cls: Type[camera_delta.CameraDelta] = (
      camera_delta.SE3CameraDelta
  )
  compute_procrustes_metric: bool = False


def define_common_flags():
  # Define the flags used by both train.py and eval.py
  flags.DEFINE_string('mode', None, 'Required by GINXM, not used.')
  flags.DEFINE_string('base_folder', None, 'Required by GINXM, not used.')
  flags.DEFINE_multi_string('gin_bindings', None, 'Gin parameter bindings.')
  flags.DEFINE_multi_string('gin_configs', None, 'Gin config files.')
  flags.DEFINE_bool('is_xm_sweep', False, 'Whether the run is an xm sweep.')


def load_config(save_config = True):
  """Loads the config, and optionally checkpoints it."""
  gin_bindings = flags.FLAGS.gin_bindings
  # Set subdirectory if this is a sweep.
  if (
      'is_xm_sweep' in flags.FLAGS
      and flags.FLAGS.is_xm_sweep
      and 'xm_xid' in flags.FLAGS
      and flags.FLAGS.xm_xid >= 0
      and flags.FLAGS.xm_wid >= 0
  ):
    xm_client = xmanager_api.XManagerApi(xm_deployment_env='alphabet')
    # Get base folder with xm parameters prefixed.
    work_unit = xm_client.get_current_work_unit()
    # Set experiment name based on parameters.
    gin_xm_params = sweep_utils.extract_gin_xm_params(
        work_unit.parameters, ['gin_bindings=Config.checkpoint_dir']
    )
    experiment_name = sweep_utils.experiment_name(gin_xm_params)
    base_dir = os.path.join(flags.FLAGS.base_folder, experiment_name)
    gin_bindings += [f'Config.checkpoint_dir="{base_dir}"']

  gin.parse_config_files_and_bindings(
      flags.FLAGS.gin_configs, flags.FLAGS.gin_bindings, skip_unknown=True
  )
  config = Config()
  if save_config and jax.host_id() == 0:
    gfile.MakeDirs(config.checkpoint_dir)
    with gfile.GFile(config.checkpoint_dir + '/config.gin', 'w') as f:
      f.write(gin.config_str())
  return config
