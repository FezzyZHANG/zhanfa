import { useQuery } from '@tanstack/react-query';
import { fetchStrategies, fetchStrategy } from '@/api/client';

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => fetchStrategies(),
  });
}

export function useStrategy(id: number) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: () => fetchStrategy(id),
    enabled: !!id,
  });
}
