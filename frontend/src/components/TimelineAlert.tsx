import { motion } from "framer-motion";

export function TimelineAlert({ t3, t0 }: { t3: number; t0: number }) {
  const hasOverdue = t0 > 0;
  return (
    <div className="sticky top-0 z-10 mb-4">
      <motion.div
        animate={hasOverdue ? { boxShadow: ["0 0 0 rgba(0,0,0,0)", "0 0 25px rgba(220,38,38,0.45)", "0 0 0 rgba(0,0,0,0)"] } : {}}
        transition={hasOverdue ? { duration: 1.6, repeat: Infinity } : {}}
        className={`border rounded-lg px-4 py-3 ${
          hasOverdue ? "border-risk-overdue/40 bg-risk-overdue/10" : "border-slate-800 bg-slate-900/40"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Timeline Alerts</div>
          <div className="text-xs text-slate-300">Daily view</div>
        </div>
        <div className="mt-2 text-sm text-slate-200">
          <span className="font-mono">T-3:</span> {t3} items{" "}
          <span className="mx-2 text-slate-600">|</span>
          <span className="font-mono">T-0:</span> {t0} items
        </div>
      </motion.div>
    </div>
  );
}

