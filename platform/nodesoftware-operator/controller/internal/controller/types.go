// types.go: shared aliases and helpers for the controller package.
package controller

import ctrl "sigs.k8s.io/controller-runtime"

// ctrlResult wraps ctrl.Result so the action handlers can express "requeue after the standard
// reconcile period" or "do not requeue" without returning a full ctrl.Result each time.
type ctrlResult = ctrl.Result

var (
	// requeue is a Result that requeues after r.ReconcilePeriod. The action handlers return
	// this when they want the loop to advance them again on the next tick (e.g. an in-flight
	// handler pod).
	requeue = ctrl.Result{RequeueAfter: 0} // overridden per-call to honour r.ReconcilePeriod

	// noRequeue is a Result that does not requeue. Used for terminal verbs (Complete, Fail).
	noRequeue = ctrl.Result{Requeue: false}
)

// ctrlLogger is a tiny alias for the controller-runtime logger so action handler signatures stay
// readable. ctrl.LoggerFromContext or log.FromContext both return *zap.SugaredLogger.
type ctrlLogger = interface {
	Info(msg string, keysAndValues ...interface{})
	Error(err error, msg string, keysAndValues ...interface{})
}
