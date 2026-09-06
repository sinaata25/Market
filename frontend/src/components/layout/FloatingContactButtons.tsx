import { getFloatingContactButtons } from "@/lib/floating-contacts-server";
import FloatingContactButtonsClient from "@/components/layout/FloatingContactButtonsClient";

export default async function FloatingContactButtons() {
  return <FloatingContactButtonsClient buttons={await getFloatingContactButtons()} />;
}
