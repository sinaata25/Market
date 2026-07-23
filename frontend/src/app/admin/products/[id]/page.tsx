"use client";

import { use } from "react";
import ProductForm from "@/components/admin/ProductForm";

export default function EditProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">ویرایش محصول</h1>
      <ProductForm productId={Number(id)} />
    </div>
  );
}
