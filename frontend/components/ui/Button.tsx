import { cn } from "@/utils/cn";

export function Button({
  className,
  variant = "primary",
  size = "default",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "default" | "small";
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        size === "default" && "px-4 py-2 text-sm",
        size === "small" && "px-3 py-1.5 text-xs",
        variant === "primary" && "bg-amber-600 text-white hover:bg-amber-700",
        variant === "secondary" && "bg-stone-200 text-stone-900 hover:bg-stone-300",
        variant === "outline" && "border border-stone-300 bg-transparent hover:bg-stone-100",
        variant === "ghost" && "hover:bg-stone-100",
        className
      )}
      {...props}
    />
  );
}
