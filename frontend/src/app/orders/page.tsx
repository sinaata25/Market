import { redirect } from "next/navigation";

// سفارش‌ها به بخش پروفایل منتقل شده است
export default function OrdersRedirect() {
  redirect("/profile/orders");
}
