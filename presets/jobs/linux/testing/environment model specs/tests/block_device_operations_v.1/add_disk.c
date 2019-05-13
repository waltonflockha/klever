/*
 * Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
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

#include <linux/module.h>
#include <linux/blkdev.h>
#include <linux/genhd.h>
#include <linux/emg/test_model.h>
#include <verifier/nondet.h>

int flip_a_coin;

int ldv_open(struct block_device *bdev, fmode_t mode)
{
	ldv_invoke_callback();
	return ldv_undef_int();
}

static const struct block_device_operations ops = {
	.open = ldv_open
};

struct gendisk disk = {
    .fops = & ops
};

static int __init ldv_init(void)
{
	flip_a_coin = ldv_undef_int();
	if (flip_a_coin) {
		ldv_register();
		add_disk(& disk);
	}
	return 0;
}

static void __exit ldv_exit(void)
{
	if (flip_a_coin) {
		del_gendisk(& disk);
		ldv_deregister();
	}
}

module_init(ldv_init);
module_exit(ldv_exit);
