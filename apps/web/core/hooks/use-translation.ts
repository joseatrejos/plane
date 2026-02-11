/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation as useBaseTranslation  } from "@plane/i18n";
import type {TTranslationStore} from "@plane/i18n";

export const useTranslation = useBaseTranslation as () => TTranslationStore;
