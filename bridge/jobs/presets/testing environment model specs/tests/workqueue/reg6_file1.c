#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/export.h>
#include <linux/workqueue.h>

static struct mutex *mtx;
static int ldv_function(void);
static struct workqueue_struct *myqueue;

static int flag1, flag2;

static void myHandler1(struct work_struct *work)
{
	if(flag1)
	{
		mutex_lock(mtx);
		mutex_lock(mtx);
	}
}

static void myHandler2(struct work_struct *work)
{
	if(flag2)
	{
		mutex_lock(mtx);
		mutex_lock(mtx);
	}
}

//Проверяем, регистрацию через queue_work_on
static int __init ldv_init(void)
{
	int ret1, ret2;
	int ret = ldv_function();
	if(!ret)
		return 0;
	myqueue = alloc_workqueue("myqueue", 0, 0);
	if(myqueue == NULL)
		return -ENOMEM;

	DECLARE_DELAYED_WORK(work1, myHandler1);
	DECLARE_DELAYED_WORK(work2, myHandler2);

	ret1 = queue_delayed_work_on(1, myqueue, &work1, 10);
	ret2 = queue_delayed_work_on(1, myqueue, &work2, 10);

	if(ret1)
		flag1 = 1;
	else
		flag1 = 0;
	if(ret2)
		flag2 = 1;
	else
		flag2 = 0;

	return 0;
}

static void __exit ldv_exit(void)
{
}

module_init(ldv_init);
module_exit(ldv_exit);
