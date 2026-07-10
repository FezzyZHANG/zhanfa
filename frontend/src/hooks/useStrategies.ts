import { useQuery } from '@tanstack/react-query';
import { fetchStrategies, fetchStrategy } from '@/api/client';

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: ({ signal }) => fetchStrategies(undefined, { signal }),
  });
}

export function useStrategy(id: number) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: ({ signal }) => fetchStrategy(id, { signal }),
    enabled: !!id,
  });
}
