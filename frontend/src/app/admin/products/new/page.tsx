"use client";

import ProductForm from "@/components/admin/ProductForm";

export default function NewProductPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">افزودن محصول جدید</h1>
      <ProductForm />
    </div>
  );
}
