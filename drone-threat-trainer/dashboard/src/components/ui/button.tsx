import * as React from "react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "cyan" | "amber";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "default", size = "default", children, ...props }, ref) => {
    let variantStyles = "bg-primary text-primary-foreground hover:bg-primary/90";
    if (variant === "destructive") {
      variantStyles = "bg-red-600 text-white hover:bg-red-700";
    } else if (variant === "outline") {
      variantStyles = "border border-border bg-transparent hover:bg-secondary text-foreground";
    } else if (variant === "secondary") {
      variantStyles = "bg-secondary text-secondary-foreground hover:bg-secondary/80";
    } else if (variant === "cyan") {
      variantStyles = "bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold shadow-lg shadow-cyan-500/20";
    } else if (variant === "amber") {
      variantStyles = "bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold shadow-lg shadow-amber-500/20";
    }

    let sizeStyles = "h-10 px-4 py-2 text-sm";
    if (size === "sm") sizeStyles = "h-8 px-3 text-xs";
    if (size === "lg") sizeStyles = "h-12 px-6 text-base font-semibold";

    const baseStyles =
      "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variantStyles} ${sizeStyles} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
