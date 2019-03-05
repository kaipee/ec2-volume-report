# ec2-volume-report
A Python script to query EC2 and report any potentially abandoned volumes

## TODO

# AWS suitable filters (exact matches and predetermined options)
- id
- region
- state
- availability-zone
- name-exact
- owner-exact
- project-exact
- type
- size-exact

# Custom filters (partial matches, int ranges, inverse matches, empty values)
- tag-contains
- name-contains
- owner-contains
- project-contains
- no-tag
- no-name
- no-owner
- no-project
- size-gt
- size-lt
- size-range-start
- size-range-end
