import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Modal } from "./Modal";

describe("Modal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  afterEach(() => {
    // Reset body overflow
    document.body.style.overflow = "";
  });

  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <Modal isOpen={false} onClose={mockOnClose}>
        Content
      </Modal>
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders modal when isOpen is true", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Modal Content
      </Modal>
    );
    expect(screen.getByText("Modal Content")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Test Title">
        Content
      </Modal>
    );
    expect(screen.getByText("Test Title")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <Modal
        isOpen={true}
        onClose={mockOnClose}
        title="Title"
        description="Test Description"
      >
        Content
      </Modal>
    );
    expect(screen.getByText("Test Description")).toBeInTheDocument();
  });

  it("renders close button by default", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Title">
        Content
      </Modal>
    );
    const closeButton = screen.getByRole("button");
    expect(closeButton).toBeInTheDocument();
  });

  it("hides close button when showCloseButton is false", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} showCloseButton={false}>
        Content
      </Modal>
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Title">
        Content
      </Modal>
    );
    fireEvent.click(screen.getByRole("button"));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    // Click on the backdrop (the element with backdrop-blur-sm)
    const backdrop = document.querySelector(".backdrop-blur-sm");
    expect(backdrop).toBeInTheDocument();
    fireEvent.click(backdrop!);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when modal content is clicked", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        <button>Inner Button</button>
      </Modal>
    );
    fireEvent.click(screen.getByText("Inner Button"));
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("calls onClose when Escape key is pressed", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose for other keys", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    fireEvent.keyDown(document, { key: "Enter" });
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("prevents body scroll when open", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body scroll when closed", () => {
    const { rerender } = render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    expect(document.body.style.overflow).toBe("hidden");

    rerender(
      <Modal isOpen={false} onClose={mockOnClose}>
        Content
      </Modal>
    );
    expect(document.body.style.overflow).toBe("");
  });

  it("applies small size class", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} size="sm">
        Content
      </Modal>
    );
    const modal = screen.getByText("Content").parentElement;
    expect(modal).toHaveClass("max-w-sm");
  });

  it("applies medium size class by default", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    const modal = screen.getByText("Content").parentElement;
    expect(modal).toHaveClass("max-w-md");
  });

  it("applies large size class", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} size="lg">
        Content
      </Modal>
    );
    const modal = screen.getByText("Content").parentElement;
    expect(modal).toHaveClass("max-w-lg");
  });

  it("applies full size class", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} size="full">
        Content
      </Modal>
    );
    const modal = screen.getByText("Content").parentElement;
    expect(modal).toHaveClass("max-w-[90vw]");
    expect(modal).toHaveClass("flex-col");
  });

  it("applies custom className", () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} className="custom-modal">
        Content
      </Modal>
    );
    const modal = screen.getByText("Content").parentElement;
    expect(modal).toHaveClass("custom-modal");
  });

  it("forwards ref to modal element", () => {
    const ref = vi.fn();
    render(
      <Modal isOpen={true} onClose={mockOnClose} ref={ref}>
        Content
      </Modal>
    );
    expect(ref).toHaveBeenCalled();
  });

  it("removes event listener when unmounted", () => {
    const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");
    const { unmount } = render(
      <Modal isOpen={true} onClose={mockOnClose}>
        Content
      </Modal>
    );
    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "keydown",
      expect.any(Function)
    );
    removeEventListenerSpy.mockRestore();
  });
});
