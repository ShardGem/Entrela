"""Confere resolução, hashes, referências e cobertura da galeria publicada."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct


def verify(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / 'manifesto.json').read_text(encoding='utf-8'))

    def file(name):
        path = (folder / name).resolve()
        if not path.is_relative_to(folder):
            raise ValueError('O manifesto contém um caminho fora da galeria.')
        return path

    scenario_file = file(manifest['scenarios_file'])
    if sha256(scenario_file.read_bytes()).hexdigest() != manifest['scenarios_sha256']:
        raise ValueError('As configurações dos cenários foram alteradas.')
    source_ids = {item['id'] for item in json.loads(scenario_file.read_text(encoding='utf-8'))}
    studies = file(manifest['studies_file'])
    if sha256(studies.read_bytes()).hexdigest() != manifest['studies_sha256']:
        raise ValueError('Os estudos documentados foram alterados.')
    analysis_ids = {item['analysis_id'] for item in json.loads(studies.read_text(encoding='utf-8'))}
    seen = set()
    for item in manifest['captures']:
        if item['file'] in seen:
            raise ValueError('Captura repetida no manifesto.')
        seen.add(item['file'])
        data = file(item['file']).read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
            raise ValueError('A captura não é um PNG válido: ' + item['file'])
        dimensions = list(struct.unpack('>II', data[16:24]))
        if dimensions != item['pixels'] or dimensions != [round(v * item['device_pixel_ratio']) for v in item['logical_size']]:
            raise ValueError('Resolução divergente: ' + item['file'])
        if sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Hash divergente: ' + item['file'])
        if item['selected_result_id'] is not None and item['selected_result_id'] not in source_ids:
            raise ValueError('Cenário de origem ausente: ' + item['file'])
        if item.get('analysis_id') is not None and item['analysis_id'] not in analysis_ids:
            raise ValueError('Estudo de origem ausente: ' + item['file'])
    missing = set(manifest['expected_pages']) - {item['page'] for item in manifest['captures']}
    if missing:
        raise ValueError('Páginas sem captura: ' + ', '.join(sorted(missing)))
    if seen != {path.relative_to(folder).as_posix() for path in folder.rglob('*.png')}:
        raise ValueError('Há imagens ausentes ou sem índice na pasta.')
    return len(seen), len(manifest['expected_pages'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    count, pages = verify(parser.parse_args().folder)
    print(f'PASS: {count} PNGs íntegros, resoluções conferidas e {pages} páginas documentadas.')
