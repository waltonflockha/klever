/*
 * Copyright (c) 2020 ISP RAS (http://www.ispras.ru)
 * Ivannikov Institute for System Programming of the Russian Academy of Sciences
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <linux/types.h>
#include <linux/fb.h>
#include <ldv/linux/fb.h>
#include <ldv/verifier/memory.h>

struct fb_info *ldv_framebuffer_alloc(size_t size)
{
	struct fb_info *info;

	info = ldv_zalloc(sizeof(struct fb_info) + size);

	if (!info)
		return NULL;

	if (size)
		info->par = (char *)info + sizeof(struct fb_info);

	return info;
}

void ldv_framebuffer_release(struct fb_info *info)
{
	if (!info)
		return;

#ifndef LDV_SPECS_SET_2_6_33
	ldv_free(info->apertures);
#endif
	ldv_free(info);
}
