import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeDefined();
  });

  it('applies default variant classes', () => {
    render(<Button>Default</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('bg-primary');
  });

  it('applies outline variant', () => {
    render(<Button variant="outline">Outline</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('border');
  });

  it('applies ghost variant', () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('hover:bg-accent');
  });

  it('applies destructive variant', () => {
    render(<Button variant="destructive">Delete</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('bg-destructive');
  });

  it('applies size classes', () => {
    render(<Button size="lg">Large</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('h-10');
  });

  it('passes through HTML button attributes', () => {
    render(<Button disabled type="submit">Submit</Button>);
    const btn = screen.getByRole('button');
    expect(btn.hasAttribute('disabled')).toBe(true);
    expect(btn.getAttribute('type')).toBe('submit');
  });
});

describe('Badge', () => {
  it('renders with text', () => {
    render(<Badge>Label</Badge>);
    expect(screen.getByText('Label')).toBeDefined();
  });

  it('applies default variant', () => {
    render(<Badge>Default</Badge>);
    const el = screen.getByText('Default');
    expect(el.className).toContain('bg-primary');
  });

  it('applies outline variant', () => {
    render(<Badge variant="outline">Outline</Badge>);
    const el = screen.getByText('Outline');
    expect(el.className).toContain('border');
  });

  it('accepts custom className', () => {
    render(<Badge className="custom-cls">Custom</Badge>);
    const el = screen.getByText('Custom');
    expect(el.className).toContain('custom-cls');
  });
});

describe('Card', () => {
  it('renders Card', () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    expect(card.className).toContain('rounded-xl');
    expect(card.textContent).toBe('Content');
  });

  it('renders CardHeader', () => {
    render(<CardHeader data-testid="header">Header</CardHeader>);
    const header = screen.getByTestId('header');
    expect(header.textContent).toBe('Header');
  });

  it('renders CardTitle', () => {
    render(<CardTitle>Title</CardTitle>);
    const title = screen.getByText('Title');
    expect(title.tagName).toBe('H3');
  });

  it('renders CardDescription', () => {
    render(<CardDescription>Description text</CardDescription>);
    const desc = screen.getByText('Description text');
    expect(desc.tagName).toBe('P');
  });

  it('renders CardContent', () => {
    render(<CardContent data-testid="content">Body</CardContent>);
    expect(screen.getByTestId('content').textContent).toBe('Body');
  });

  it('composes Card subcomponents', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Card</CardTitle>
          <CardDescription>A description</CardDescription>
        </CardHeader>
        <CardContent>Body content</CardContent>
      </Card>
    );
    expect(screen.getByText('Test Card')).toBeDefined();
    expect(screen.getByText('A description')).toBeDefined();
    expect(screen.getByText('Body content')).toBeDefined();
  });
});

describe('Skeleton', () => {
  it('renders skeleton div', () => {
    const { container } = render(<Skeleton />);
    const div = container.firstChild as HTMLElement;
    expect(div.className).toContain('animate-pulse');
    expect(div.className).toContain('bg-muted');
  });

  it('accepts custom className', () => {
    const { container } = render(<Skeleton className="h-10 w-full" />);
    const div = container.firstChild as HTMLElement;
    expect(div.className).toContain('h-10');
    expect(div.className).toContain('w-full');
  });
});
