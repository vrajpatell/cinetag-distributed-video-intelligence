'use client';

import { motion, type HTMLMotionProps } from 'motion/react';
import { cn } from '@/lib/utils';

type FadeInProps = HTMLMotionProps<'div'> & {
  delay?: number;
  duration?: number;
};

export function FadeIn({ className, delay = 0, duration = 0.35, children, ...props }: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, delay, ease: [0.22, 1, 0.36, 1] }}
      className={cn(className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function StaggerChildren({
  className,
  stagger = 0.06,
  children,
}: {
  className?: string;
  stagger?: number;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: stagger } },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 14 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function ScaleOnHover({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.01 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
