-- pandoc_strip_images.lua
-- Drops all images from the Pandoc AST before the writer renders.
-- Catches both native Image nodes (embedded DOCX/ODT images) and raw HTML
-- <img>/<figure> passthroughs that the CommonMark writer would otherwise
-- emit verbatim. Empty paragraphs left behind by image-only paragraphs are
-- also removed so the output doesn't gain stray blank lines.

function Image(_)
    return {}
end

function RawInline(elem)
    if elem.format == 'html' and elem.text:lower():match('^<img') then
        return {}
    end
end

function RawBlock(elem)
    if elem.format == 'html' then
        local s = elem.text:lower()
        if s:match('^%s*<img') or s:match('^%s*<figure') then
            return {}
        end
    end
end

function Para(elem)
    if #elem.content == 0 then return {} end
end

function Plain(elem)
    if #elem.content == 0 then return {} end
end
