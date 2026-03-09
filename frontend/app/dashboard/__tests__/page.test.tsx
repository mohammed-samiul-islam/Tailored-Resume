import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DashboardPage from "../page";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("DashboardPage", () => {
  it("renders dashboard title", () => {
    render(<DashboardPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeInTheDocument();
  });

  it("shows Generate resume button disabled when no selection", () => {
    render(<DashboardPage />, { wrapper });
    const btn = screen.getByRole("button", { name: /generate resume/i });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/Select a resume and a job from the cards above/i)).toBeInTheDocument();
  });

  it("has upload and analyze sections", () => {
    render(<DashboardPage />, { wrapper });
    expect(screen.getByText(/upload resume/i)).toBeInTheDocument();
    expect(screen.getByText(/add job description/i)).toBeInTheDocument();
  });
});
