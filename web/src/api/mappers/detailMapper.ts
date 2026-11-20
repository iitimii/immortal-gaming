import type { DetailResponseDTO } from '@/types/api';
import type { AvatarDetail, POIDetail, RegionDetail, SectDetail } from '@/types/core';
import type { SelectionType } from '@/stores/ui';

type DetailDomainByType<T extends SelectionType> =
  T extends 'avatar'
    ? AvatarDetail
    : T extends 'region'
      ? RegionDetail
      : T extends 'sect'
        ? SectDetail
        : POIDetail;

/**
 * Normalize the DTO returned by /api/v1/query/detail into a frontend domain model.
 *
 * The backend already returns objects close to the domain shape, so this mainly:
 * - narrows the union type based on the caller's target.type
 * - keeps an extension point for future mapping
 */
export function mapDetailDTOToDomain(
  dto: DetailResponseDTO,
  targetType: 'avatar',
): AvatarDetail;
export function mapDetailDTOToDomain(
  dto: DetailResponseDTO,
  targetType: 'region',
): RegionDetail;
export function mapDetailDTOToDomain(
  dto: DetailResponseDTO,
  targetType: 'sect',
): SectDetail;
export function mapDetailDTOToDomain(
  dto: DetailResponseDTO,
  targetType: 'poi',
): POIDetail;
export function mapDetailDTOToDomain<T extends SelectionType>(
  dto: DetailResponseDTO,
  targetType: T,
): DetailDomainByType<T>;
export function mapDetailDTOToDomain(
  dto: DetailResponseDTO,
  _targetType: SelectionType,
): AvatarDetail | RegionDetail | SectDetail | POIDetail {
  return dto;
}

