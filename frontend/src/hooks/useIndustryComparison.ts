import { useQuery } from '@tanstack/react-query';
import { fetchIndustryComparison } from '@/api/client';

export function useIndustryComparison(industry: string) {
  return useQuery({
    queryKey: ['industryComparison', industry],
    queryFn: () => fetchIndustryComparison(industry),
    enabled: !!industry,
  });
}
