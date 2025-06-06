// Copyright 2025 The Google Research Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef SCANN_OSS_WRAPPERS_SCANN_ALIGNED_MALLOC_H_
#define SCANN_OSS_WRAPPERS_SCANN_ALIGNED_MALLOC_H_

#include <cstdlib>

namespace research_scann {

void *aligned_malloc(size_t size, size_t minimum_alignment);
void aligned_free(void *aligned_memory);

}  // namespace research_scann

#endif
