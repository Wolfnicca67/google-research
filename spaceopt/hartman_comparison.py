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

"""Comparison experiments for Hartman6d."""
import jax.numpy as jnp
import spaceopt.launch_template_comparison as template
from spaceopt.synthetic_objective_functions import hartman6d as hartman6d_fn

search_space = jnp.array([[0., 1.], [0., 1.], [0., 1.], [0., 1.], [0., 1.],
                          [0., 1.]])

objective_fn = hartman6d_fn


def run_exp(key,
            budget,
            budget_b1,
            params,
            num_rounds,
            sampling_method_primary,
            sampling_method_secondary,
            num_init=None,
            batch_size=None,
            reduce_rates=None,
            num_pnts_for_af=1000,
            num_steps_for_gp=1000,
            num_x_for_score=1000,
            num_y_for_score=1000,
            num_ss_per_rate=200,
            sampling_gp_method='tfp',
            x_precollect=None,
            y_precollect=None,
            additional_info_precollect=None):
  """Run head-2-head comparisons for Hartman6d."""
  results_all = template.launch_comparison(
      key=key,
      objective_fn=objective_fn,
      search_space=search_space,
      budget=budget,
      budget_b1=budget_b1,
      params=params,
      num_rounds=num_rounds,
      sampling_method_primary=sampling_method_primary,
      sampling_method_secondary=sampling_method_secondary,
      num_init=num_init,
      batch_size=batch_size,
      num_pnts_for_af=num_pnts_for_af,
      num_steps_for_gp=num_steps_for_gp,
      reduce_rates=reduce_rates,
      num_x_for_score=num_x_for_score,
      num_y_for_score=num_y_for_score,
      num_ss_per_rate=num_ss_per_rate,
      sampling_gp_method=sampling_gp_method,
      x_precollect=x_precollect,
      y_precollect=y_precollect,
      additional_info_precollect=additional_info_precollect)
  return results_all
