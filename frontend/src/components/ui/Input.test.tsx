import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "./Input";
import { Search, Eye } from "lucide-react";

describe("Input", () => {
  it("renders input element", () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<Input label="Username" />);
    expect(screen.getByText("Username")).toBeInTheDocument();
  });

  it("associates label with input via htmlFor", () => {
    render(<Input label="Email" />);
    const label = screen.getByText("Email");
    const input = screen.getByRole("textbox");
    expect(label).toHaveAttribute("for", "email");
    expect(input).toHaveAttribute("id", "email");
  });

  it("uses custom id when provided", () => {
    render(<Input id="custom-id" label="Custom" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("id", "custom-id");
  });

  it("displays error message", () => {
    render(<Input error="This field is required" />);
    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("applies error styling when error is present", () => {
    render(<Input error="Error" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveClass("border-red-300");
  });

  it("displays helper text", () => {
    render(<Input helperText="Enter your email address" />);
    expect(screen.getByText("Enter your email address")).toBeInTheDocument();
  });

  it("prioritizes error over helper text", () => {
    render(<Input error="Error" helperText="Helper" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.queryByText("Helper")).not.toBeInTheDocument();
  });

  it("renders left icon", () => {
    render(<Input leftIcon={<Search data-testid="left-icon" />} />);
    expect(screen.getByTestId("left-icon")).toBeInTheDocument();
  });

  it("renders right icon", () => {
    render(<Input rightIcon={<Eye data-testid="right-icon" />} />);
    expect(screen.getByTestId("right-icon")).toBeInTheDocument();
  });

  it("applies padding for left icon", () => {
    render(<Input leftIcon={<Search />} />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveClass("pl-10");
  });

  it("applies padding for right icon", () => {
    render(<Input rightIcon={<Eye />} />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveClass("pr-10");
  });

  it("handles value changes", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} />);

    const input = screen.getByRole("textbox");
    await user.type(input, "hello");

    expect(handleChange).toHaveBeenCalled();
    expect(input).toHaveValue("hello");
  });

  it("supports controlled value", () => {
    render(<Input value="controlled" onChange={() => {}} />);
    expect(screen.getByRole("textbox")).toHaveValue("controlled");
  });

  it("supports disabled state", () => {
    render(<Input disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("supports readonly state", () => {
    render(<Input readOnly value="readonly" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("readonly");
  });

  it("supports different input types", () => {
    render(<Input type="email" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("type", "email");
  });

  it("supports password type", () => {
    render(<Input type="password" />);
    const input = document.querySelector('input[type="password"]');
    expect(input).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<Input className="custom-class" />);
    const input = screen.getByRole("textbox");
    expect(input).toHaveClass("custom-class");
  });

  it("forwards ref to input element", () => {
    const ref = vi.fn();
    render(<Input ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it("handles focus events", () => {
    const handleFocus = vi.fn();
    render(<Input onFocus={handleFocus} />);

    fireEvent.focus(screen.getByRole("textbox"));
    expect(handleFocus).toHaveBeenCalledTimes(1);
  });

  it("handles blur events", () => {
    const handleBlur = vi.fn();
    render(<Input onBlur={handleBlur} />);

    const input = screen.getByRole("textbox");
    fireEvent.focus(input);
    fireEvent.blur(input);
    expect(handleBlur).toHaveBeenCalledTimes(1);
  });
});
