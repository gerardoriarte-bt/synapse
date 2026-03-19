import React from 'react';

export const SkeletonLoader: React.FC = () => {
  return (
    <div className="w-full space-y-4 animate-pulse p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
      <div className="h-4 bg-zinc-800 rounded w-3/4"></div>
      <div className="h-4 bg-zinc-800 rounded w-1/2"></div>
      
      {/* Chart-like skeleton */}
      <div className="flex items-end gap-2 h-40 pt-10">
        <div className="w-full bg-zinc-800 rounded-t h-[30%]"></div>
        <div className="w-full bg-zinc-800 rounded-t h-[60%]"></div>
        <div className="w-full bg-zinc-800 rounded-t h-[45%]"></div>
        <div className="w-full bg-zinc-800 rounded-t h-[80%]"></div>
        <div className="w-full bg-zinc-800 rounded-t h-[50%]"></div>
      </div>
      
      <div className="flex justify-between">
        <div className="h-3 bg-zinc-800 rounded w-20"></div>
        <div className="h-3 bg-zinc-800 rounded w-20"></div>
        <div className="h-3 bg-zinc-800 rounded w-20"></div>
      </div>
    </div>
  );
};
