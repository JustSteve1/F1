
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import type { Database } from '@/integrations/supabase/types';

type Session = Database['public']['Tables']['sessions']['Row'];

export function useF1Sessions() {
  return useQuery({
    queryKey: ['f1-sessions'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('sessions')
        .select('*')
        .order('start_time', { ascending: false });

      if (error) {
        throw error;
      }

      return data as Session[];
    },
  });
}

export function useCurrentF1Session() {
  return useQuery({
    queryKey: ['current-f1-session'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('sessions')
        .select('*')
        .eq('status', 'Live')
        .single();

      if (error && error.code !== 'PGRST116') { // PGRST116 is the "no rows returned" error
        throw error;
      }

      return data as Session | null;
    },
  });
}
