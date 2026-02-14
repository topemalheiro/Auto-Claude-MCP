"use client";

import { useSpec } from "@/hooks";
import { useParams } from "next/navigation";

export default function SpecPage() {
  const params = useParams();
  const specId = params.id as string;
  const { spec, isLoading } = useSpec(specId);

  if (isLoading) {
    return <div className="p-8">Loading spec...</div>;
  }

  if (!spec) {
    return <div className="p-8">Spec not found</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">{(spec as any).name}</h1>
      <pre className="mt-4 rounded-lg bg-gray-100 p-4">
        {(spec as any).content}
      </pre>
    </div>
  );
}
