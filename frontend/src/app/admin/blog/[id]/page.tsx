"use client";

import { use } from "react";
import BlogPostForm from "@/components/admin/BlogPostForm";

export default function EditBlogPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <div className="space-y-4"><h1 className="text-lg font-bold text-slate-800">ویرایش نوشته وبلاگ</h1><BlogPostForm postId={Number(id)} /></div>;
}
