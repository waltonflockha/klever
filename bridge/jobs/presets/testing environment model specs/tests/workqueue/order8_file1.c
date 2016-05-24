#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/export.h>
#include <linux/workqueue.h>

static struct mutex *mtx;
static int ldv_function(void);
static struct workqueue_struct *myqueue;

static struct delayed_work work1, work2, work3, work4;

static void myHandler(struct work_struct *work)
{
	mutex_lock(mtx);
}

//Проверяем, что flush_delayed_work действительно вызывает work
static int __init ldv_init(void)
{
	myqueue = alloc_workqueue("myqueue", 0, 0);
	if(myqueue == NULL)
		return -ENOMEM;

	INIT_DELAYED_WORK(&work1, myHandler);
	INIT_DELAYED_WORK(&work2, myHandler);
	INIT_DELAYED_WORK(&work3, myHandler);
	INIT_DELAYED_WORK(&work4, myHandler);

	queue_delayed_work(myqueue, &work1, 10);
	queue_delayed_work(myqueue, &work2, 10);
	queue_delayed_work(myqueue, &work3, 10);
	queue_delayed_work(myqueue, &work4, 10);

	flush_delayed_work(&work1);
	mutex_unlock(mtx);
	flush_delayed_work(&work2);
	mutex_unlock(mtx);
	flush_delayed_work(&work3);
	mutex_unlock(mtx);
	flush_delayed_work(&work4);
	mutex_unlock(mtx);

	return 0;
}

static void __exit ldv_exit(void)
{
	mutex_lock(mtx);
	mutex_unlock(mtx);
}

module_init(ldv_init);
module_exit(ldv_exit);
