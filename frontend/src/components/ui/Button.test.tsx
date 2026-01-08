import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "./Button";
import { Plus } from "lucide-react";

describe("Button", () => {
  it("renders children correctly", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
  });

  it("applies primary variant by default", () => {
    render(<Button>Primary</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("from-primary-500");
  });

  it("applies secondary variant when specified", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("bg-surface-100");
  });

  it("applies danger variant when specified", () => {
    render(<Button variant="danger">Delete</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("from-red-500");
  });

  it("applies ghost variant when specified", () => {
    render(<Button variant="ghost">Ghost</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("bg-transparent");
  });

  it("applies outline variant when specified", () => {
    render(<Button variant="outline">Outline</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("border-primary-500");
  });

  it("applies small size when specified", () => {
    render(<Button size="sm">Small</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("px-3", "py-1.5", "text-xs");
  });

  it("applies medium size by default", () => {
    render(<Button>Medium</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("px-4", "py-2.5", "text-sm");
  });

  it("applies large size when specified", () => {
    render(<Button size="lg">Large</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("px-6", "py-3", "text-base");
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("is disabled when isLoading is true", () => {
    render(<Button isLoading>Loading</Button>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("shows loading spinner when isLoading is true", () => {
    render(<Button isLoading>Loading</Button>);
    const button = screen.getByRole("button");
    // Check for the spinning loader icon (svg with animate-spin class)
    const loader = button.querySelector(".animate-spin");
    expect(loader).toBeInTheDocument();
  });

  it("renders left icon when provided", () => {
    render(<Button leftIcon={<Plus data-testid="left-icon" />}>Add</Button>);
    expect(screen.getByTestId("left-icon")).toBeInTheDocument();
  });

  it("renders right icon when provided", () => {
    render(<Button rightIcon={<Plus data-testid="right-icon" />}>Add</Button>);
    expect(screen.getByTestId("right-icon")).toBeInTheDocument();
  });

  it("hides right icon when isLoading is true", () => {
    render(
      <Button isLoading rightIcon={<Plus data-testid="right-icon" />}>
        Add
      </Button>
    );
    expect(screen.queryByTestId("right-icon")).not.toBeInTheDocument();
  });

  it("calls onClick handler when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("does not call onClick when disabled", () => {
    const handleClick = vi.fn();
    render(
      <Button disabled onClick={handleClick}>
        Click me
      </Button>
    );
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("applies custom className", () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveClass("custom-class");
  });

  it("forwards ref to button element", () => {
    const ref = vi.fn();
    render(<Button ref={ref}>Ref</Button>);
    expect(ref).toHaveBeenCalled();
  });
});
