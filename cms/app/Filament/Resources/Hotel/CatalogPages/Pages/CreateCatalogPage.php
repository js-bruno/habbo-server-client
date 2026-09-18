<?php

namespace App\Filament\Resources\Hotel\CatalogPages\Pages;

use App\Filament\Resources\Hotel\CatalogPages\CatalogPageResource;
use Filament\Resources\Pages\CreateRecord;

class CreateCatalogPage extends CreateRecord
{
    protected static string $resource = CatalogPageResource::class;

    protected function getHeaderActions(): array
    {
        return [

        ];
    }
}
